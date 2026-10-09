from aiogram.fsm.state import State, StatesGroup


class NutritionStates(StatesGroup):
    choosing_meal = State()
    entering_meal_time = State()
    editing_entry = State()
    browsing_catalog = State()
    searching_product = State()
    entering_amount = State()
    reviewing = State()
    saving = State()
    product_name = State()
    product_brand = State()
    product_kcal = State()
    product_protein = State()
    product_fat = State()
    product_carbs = State()
    product_sugar = State()
    product_fiber = State()
    naming_dish = State()
    editing_product_field = State()
