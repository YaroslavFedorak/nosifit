"""What the OpenAPI description cannot read from the routes themselves.

api/openapi.py takes paths, methods and parameters from the URL map and the
views. This module adds who may call each operation and, for the operations
described so far, the request and response bodies. Every response schema
here is checked against real responses in web/tests/unit/test_openapi.py;
operations not listed in OPERATIONS are published with an undescribed body.

Schemas list as ``required`` only the fields every response carries.
"""

STR = {"type": "string"}
INT = {"type": "integer"}
NUM = {"type": "number"}
BOOL = {"type": "boolean"}
DATE = {"type": "string", "format": "date"}
ANY_OBJECT = {"type": "object"}


def nullable(schema):
    return {**schema, "type": [schema["type"], "null"]}


def arr(items):
    return {"type": "array", "items": items}


def obj(required=(), **properties):
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = sorted(required)
    return schema


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


# --- Who may call what ----------------------------------------------------------------

# By blueprint (legacy name); OPERATIONS may override per endpoint.
AUTH_BY_BLUEPRINT = {
    "telegram_api": "bot",
    "i18n": "public",
}
DEFAULT_AUTH = "session"

TAGS = {
    "dashboard_api": "dashboard",
    "training_dashboard_api": "dashboard",
    "equipment_api": "equipment",
    "i18n": "translations",
    "injury_api": "injuries",
    "nutrition_api": "nutrition",
    "onboarding_api": "onboarding",
    "recovery": "recovery",
    "telegram_api": "telegram",
    "training_api": "training",
}


# --- Shared schemas ---------------------------------------------------------------------

STATUS = obj(["status"], status=STR)

SCHEMAS = {
    "Error": obj(
        ["code", "message", "error"],
        code={"type": "string", "pattern": "^[a-z][a-z0-9_]*$", "description": "Stable, machine-readable."},
        message={"type": "string", "description": "Human-readable; never internals."},
        error={"description": "Kept for older clients: a code or a message, as each endpoint returned before."},
        details={"type": "object", "description": "Extra data, where an endpoint has some."},
    ),
    "Status": STATUS,
    "MealItem": obj(
        ["id", "name", "calories", "protein", "fat", "carbs"],
        id=INT,
        name=STR,
        product_id=nullable(INT),
        dish_id=nullable(INT),
        dish_name=nullable(STR),
        amount=nullable(NUM),
        unit=nullable(STR),
        weight=nullable(NUM),
        liquid_ml=nullable(NUM),
        calories=NUM,
        protein=NUM,
        fat=NUM,
        carbs=NUM,
        fiber=nullable(NUM),
        sugar=nullable(NUM),
        salt=nullable(NUM),
        saturated_fat=nullable(NUM),
    ),
    "Meal": obj(
        ["id", "name", "category", "date", "time", "items", "total_calories", "total_protein", "total_fat",
         "total_carbs", "fiber_complete", "sugar_complete"],
        id=INT,
        name=STR,
        category={"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
        date=DATE,
        time=nullable(STR),
        items=arr(ref("MealItem")),
        total_calories=NUM,
        total_protein=NUM,
        total_fat=NUM,
        total_carbs=NUM,
        total_fiber=nullable(NUM),
        total_sugar=nullable(NUM),
        fiber_complete=BOOL,
        sugar_complete=BOOL,
    ),
    "NutritionDay": obj(
        ["kcal", "kcal_goal", "meals", "goals", "macros_ratio"],
        kcal=NUM,
        kcal_goal=NUM,
        kcal_percent=NUM,
        kcal_balance=NUM,
        carb=NUM,
        fat=NUM,
        fiber=nullable(NUM),
        current_weight=nullable(NUM),
        balance_status=STR,
        goals=obj(["calories", "protein", "fat", "carbs"], calories=NUM, protein=NUM, fat=NUM, carbs=NUM, fiber=NUM),
        macros_ratio=obj(["protein", "fat", "carbs"], protein=NUM, fat=NUM, carbs=NUM),
        meals=arr(ref("Meal")),
    ),
    "Water": obj(["amount", "recommended"], amount=NUM, recommended=NUM, status=STR),
    "Weight": obj(["weight"], weight=nullable(NUM), bmi=nullable(NUM), status=STR),
    "Product": obj(
        ["id", "name", "category", "kcal_per_100g", "protein_per_100g", "fat_per_100g", "carbs_per_100g",
         "is_favorite", "is_own"],
        id=INT,
        name=STR,
        brand=nullable(STR),
        barcode=nullable(STR),
        category=STR,
        kcal_per_100g=NUM,
        protein_per_100g=NUM,
        fat_per_100g=NUM,
        carbs_per_100g=NUM,
        fiber_per_100g=nullable(NUM),
        sugar_per_100g=nullable(NUM),
        default_unit=STR,
        grams_per_unit=nullable(NUM),
        is_favorite=BOOL,
        is_own=BOOL,
        verified=BOOL,
        source=STR,
    ),
    "ProductList": obj(["products", "has_more"], products=arr(ref("Product")), has_more=BOOL),
    "DashboardDay": obj(
        ["date", "daily_score", "training", "nutrition", "recovery"],
        date=DATE,
        daily_score=NUM,
        training=obj(
            ["score", "completed", "duration", "exercise_count"],
            score=nullable(NUM),
            completed=BOOL,
            duration=INT,
            exercise_count=INT,
        ),
        nutrition=obj(["score", "calories", "protein", "water"], score=nullable(NUM), calories=NUM, protein=NUM, water=NUM),
        recovery=obj(
            ["score", "sleep_hours", "habits_completed", "habits_total"],
            score=nullable(NUM),
            sleep_hours=NUM,
            habits_completed=INT,
            habits_total=INT,
        ),
    ),
    "TrainingPlan": obj(
        ["id", "user_id", "name", "is_active", "days"],
        id=INT,
        user_id=INT,
        name=STR,
        is_active=BOOL,
        days=ANY_OBJECT,
        created_at=nullable(STR),
        updated_at=nullable(STR),
    ),
    "Injury": obj(["id", "name"], id=INT, name=STR, description=nullable(STR)),
    "RecoveryHabit": obj(
        ["id", "slug", "name", "points", "premium_only"],
        id=INT,
        slug=STR,
        name=STR,
        description=nullable(STR),
        category=nullable(STR),
        points=INT,
        icon=nullable(STR),
        recommended_when={"type": ["array", "null"]},
        premium_only=BOOL,
    ),
}

TELEGRAM_USER_ID = {"type": "integer", "minimum": 1, "description": "Telegram's numeric user id."}

# --- Operations ---------------------------------------------------------------------------
#
# Keyed by endpoint (the unversioned registration). Fields:
#   summary, auth ("session" | "bot" | "public"), request (schema),
#   status (success code, default 200), response (schema), errors (extra
#   codes), required_query (query parameters the operation cannot do without).

OPERATIONS = {
    # Translations
    "i18n.get_translation": {
        "summary": "Translations of one namespace; keys missing in the locale fall back to Ukrainian.",
        "response": {"type": "object", "description": "Nested object of translated strings."},
    },
    # Injuries
    "injury_api.list_injuries": {
        "summary": "The injury catalog.",
        "auth": "public",
        "response": arr(ref("Injury")),
    },
    "injury_api.set_user_injuries": {
        "summary": "Replace the user's injuries.",
        "request": obj(["injuries"], injuries=arr(INT)),
        "response": ref("Status"),
        "errors": [400],
    },
    # Equipment
    "equipment_api.get_equipment": {
        "summary": "Equipment the user has.",
        "response": arr(ANY_OBJECT),
    },
    # Dashboard
    "dashboard_api.today": {"summary": "Today's scores for training, nutrition and recovery.", "response": ref("DashboardDay")},
    "dashboard_api.heatmap": {
        "summary": "The last 365 days that have any data, with a 0-6 level each.",
        "response": obj(
            ["days", "start_date", "end_date"],
            days=arr({"allOf": [ref("DashboardDay"), obj(["level"], level=INT)]}),
            start_date=DATE,
            end_date=DATE,
        ),
    },
    # Nutrition
    "nutrition_api.api_day": {"summary": "Today's meals, totals and goals.", "response": ref("NutritionDay")},
    "nutrition_api.api_today": {"summary": "Same as /nutrition/day.", "response": ref("NutritionDay")},
    "nutrition_api.api_add_meal": {
        "summary": "Create a meal.",
        "request": obj(
            [],
            category={"type": "string", "description": "breakfast, lunch, dinner or snack (aliases accepted)"},
            name=STR,
            date=DATE,
            time=STR,
        ),
        "status": 201,
        "response": ref("Meal"),
        "errors": [400],
    },
    "nutrition_api.api_edit_meal": {
        "summary": "Change a meal's category.",
        "request": obj(["category"], category=STR),
        "response": ref("Meal"),
        "errors": [400, 404],
    },
    "nutrition_api.api_delete_meal": {"summary": "Delete a meal and its entries.", "response": ref("Status"), "errors": [404]},
    "nutrition_api.api_add_item": {
        "summary": "Add an entry to a meal (a catalog product or free-form values).",
        "request": obj(
            ["meal_id"],
            meal_id=INT,
            product_id=INT,
            name=STR,
            amount=NUM,
            unit=STR,
            calories=NUM,
            protein=NUM,
            fat=NUM,
            carbs=NUM,
        ),
        "status": 201,
        "response": obj(["id", "status"], id=INT, status=STR),
        "errors": [400, 404],
    },
    "nutrition_api.api_get_water": {"summary": "Water drunk today.", "response": ref("Water")},
    "nutrition_api.api_add_water": {
        "summary": "Add water (liters).",
        "request": obj(["amount"], amount=NUM),
        "response": ref("Water"),
        "errors": [400],
    },
    "nutrition_api.api_get_weight": {"summary": "Latest body weight and BMI.", "response": ref("Weight")},
    "nutrition_api.api_update_weight": {
        "summary": "Record today's body weight (kg).",
        "request": obj(["weight"], weight=NUM),
        "response": ref("Weight"),
        "errors": [400],
    },
    "nutrition_api.api_products": {"summary": "Search the product catalog.", "response": ref("ProductList")},
    # Training
    "training_api.plans": {"summary": "The user's training plans.", "response": arr(ref("TrainingPlan"))},
    "training_api.create_plan": {
        "summary": "Create a plan; an active plan deactivates the others.",
        "request": obj([], name=STR, is_active=BOOL, days=ANY_OBJECT),
        "response": ref("TrainingPlan"),
        "errors": [400],
    },
    "training_api.update_plan": {
        "summary": "Rename, re-plan or (de)activate a plan.",
        "request": obj([], name=STR, is_active=BOOL, days=ANY_OBJECT),
        "response": ref("TrainingPlan"),
        "errors": [400, 404],
    },
    "training_api.delete_plan": {"summary": "Delete a plan.", "response": ref("Status"), "errors": [404]},
    "training_api.start_session": {
        "summary": "Start a live session, or return the one in progress.",
        "request": obj([], fatigue_before=INT),
        "response": obj(["id"], id=INT),
        "errors": [400],
    },
    "training_api.strength_test": {
        "summary": "Record a strength test.",
        "request": obj([], pushups=INT, squats=INT, situps=INT),
        "response": obj(
            ["status", "raw_performance"],
            status=STR,
            raw_performance=obj(["pushups", "squats", "situps"], pushups=INT, squats=INT, situps=INT),
        ),
        "errors": [400],
    },
    "training_api.today_logged_session": {
        "summary": "The latest session started today, if any.",
        "response": obj(["session"], session=nullable(ANY_OBJECT)),
    },
    "training_api.exercises": {
        "summary": "The exercise catalog, one page at a time.",
        "response": obj(["items", "page", "per_page", "total"], items=arr(ANY_OBJECT), page=INT, per_page=INT, total=INT),
    },
    "training_api.search_exercise_catalog": {
        "summary": "Exercises matching a name or slug, done-before first.",
        "response": obj(["items", "query", "has_more"], items=arr(ANY_OBJECT), query=STR, has_more=BOOL),
    },
    "training_api.heatmap": {
        "summary": "Training stress per day of a year.",
        "response": obj(
            ["days"],
            days=arr(
                obj(
                    ["date", "hard_sets", "session_training_stress_proxy", "intensity_percent", "is_today"],
                    date=DATE,
                    hard_sets=NUM,
                    session_training_stress_proxy=NUM,
                    intensity_percent=NUM,
                    is_today=BOOL,
                )
            ),
        ),
        "errors": [400],
    },
    # Recovery
    "recovery.get_habits_list": {"summary": "The habit catalog.", "response": arr(ref("RecoveryHabit"))},
    "recovery.get_day_details": {
        "summary": "Sleep, habits and training of one day (the URL id must be the signed-in user).",
        "required_query": ["date"],
        "errors": [400],
    },
    "recovery.get_snapshot": {
        "summary": "The user's recovery snapshot of a day (the URL id must be the signed-in user).",
        "response": obj(["snapshot"], snapshot=nullable(ANY_OBJECT)),
        "errors": [400, 404],
    },
    # Telegram bot
    "telegram_api.telegram_login": {
        "summary": "Sign a linked Telegram user in; the answer sets the session cookie.",
        "request": obj(["telegram_user_id"], telegram_user_id=TELEGRAM_USER_ID, username=STR, restore=BOOL),
        "response": obj(["status", "username"], status=STR, username=STR),
        "errors": [404, 429],
    },
    "telegram_api.telegram_logout": {
        "summary": "Stop restoring the bot session until the next explicit login.",
        "request": obj(["telegram_user_id"], telegram_user_id=TELEGRAM_USER_ID),
        "response": ref("Status"),
    },
    "telegram_api.register_start": {
        "summary": "Email a registration code (or, for a registered address, a notice). Same answer either way.",
        "request": obj(["telegram_user_id", "email"], telegram_user_id=TELEGRAM_USER_ID, email=STR),
        "response": obj(["status"], status={"type": "string", "enum": ["code_sent"]}),
        "errors": [409, 429, 503],
    },
    "telegram_api.register_verify": {
        "summary": "Create the account with the emailed code and sign in.",
        "request": obj(
            ["telegram_user_id", "email", "code"],
            telegram_user_id=TELEGRAM_USER_ID,
            email=STR,
            code={"type": "string", "pattern": "^[0-9]{6}$"},
            name=STR,
            username=STR,
        ),
        "status": 201,
        "response": obj(["status", "username"], status=STR, username=STR),
        "errors": [409, 429],
    },
    "telegram_api.link_token": {
        "summary": "A one-time link that connects this Telegram account to a signed-in website account.",
        "request": obj(
            ["telegram_user_id"],
            telegram_user_id=TELEGRAM_USER_ID,
            username=STR,
            name=STR,
            via={"type": "string", "enum": ["google", "github", "password"]},
        ),
        "response": obj(["url", "expires_in"], url=STR, expires_in=INT),
        "errors": [409, 429, 503],
    },
}
