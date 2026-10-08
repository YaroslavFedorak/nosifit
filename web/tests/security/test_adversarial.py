"""Second, independent adversarial pass.

Each test is written from the point of view of an attacker with a normal
account (or a stolen session) who can craft any HTTP request.
"""

from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models import Meal, MealItem, Product, ProductName
from backend.app.models.user import User
from backend.app.utils.token import generate_reset_token

PASSWORD = "password123"


def login(client, email="test@example.com", password=PASSWORD):
    return client.post("/auth/login", data={"email": email, "password": password})


@pytest.fixture
def victim(app):
    user = User(
        username="victim",
        email="victim@example.com",
        password=generate_password_hash("victim-password"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_private_product(owner, name="secret recipe"):
    product = Product(
        owner_user_id=owner.id,
        source="user",
        kcal_per_100g=100,
        protein_per_100g=1,
        fat_per_100g=1,
        carbs_per_100g=1,
        fiber_per_100g=0,
        liquid_ml_per_100g=0,
        category="other",
        default_unit="g",
        grams_per_unit=1,
    )
    db.session.add(product)
    db.session.flush()
    db.session.add(ProductName(product_id=product.id, locale="uk", name=name))
    db.session.commit()
    return product


# --- Account takeover chains ---------------------------------------------------------


@pytest.fixture
def sent_mail(monkeypatch):
    sent = []

    def fake_send(to, subject, text, html=None):
        sent.append({"to": to, "text": text})

    monkeypatch.setattr("backend.app.utils.email_service.send_email", fake_send)
    monkeypatch.setattr("web.app.routes.profile.email_change.send_email", fake_send)
    monkeypatch.setattr(
        "web.app.routes.profile.email_change.send_email_code",
        lambda email, code: sent.append({"to": email, "code": code}),
    )
    return sent


def test_stolen_session_cannot_change_email_without_password(client, user, sent_mail):
    """Stolen cookie -> change email to attacker's -> reset password = takeover."""
    login(client)

    response = client.post(
        "/profile/change_email", json={"new_email": "attacker@example.com"}
    )

    assert response.status_code == 400
    assert not any(m["to"] == "attacker@example.com" for m in sent_mail)


def test_email_change_with_password_works_and_notifies_old_address(client, user, sent_mail):
    login(client)

    response = client.post(
        "/profile/change_email",
        json={"new_email": "new@example.com", "password": PASSWORD},
    )
    assert response.json["status"] == "sent"
    code = next(m["code"] for m in sent_mail if m["to"] == "new@example.com")

    response = client.post("/profile/confirm_email", json={"code": code})
    assert response.json["status"] == "success"

    db.session.refresh(user)
    assert user.email == "new@example.com"
    assert any(m["to"] == "test@example.com" and "code" not in m for m in sent_mail)


def test_email_change_accepts_the_profile_form(client, user, sent_mail):
    """The profile modal posts a regular form, not JSON."""
    login(client)

    response = client.post(
        "/profile/change_email",
        data={"new_email": "new@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json["status"] == "sent"


def test_password_reset_link_ignores_spoofed_host(client, user, sent_mail, app):
    """Host-header poisoning: the emailed link must point at our own site."""
    app.config["PUBLIC_BASE_URL"] = "https://nosifit.example"

    client.post(
        "/auth/reset",
        data={"email": "test@example.com"},
        headers={"X-Forwarded-Host": "evil.example", "Host": "evil.example"},
    )

    text = next(m["text"] for m in sent_mail if m["to"] == "test@example.com")
    assert "evil.example" not in text
    assert "https://nosifit.example/auth/reset/" in text


def test_reset_link_dies_when_email_changes(client, user):
    """A link sent to the old (possibly compromised) mailbox must stop working."""
    with client.application.test_request_context():
        token = generate_reset_token(user)

    user.email = "moved@example.com"
    db.session.commit()

    response = client.post(
        f"/auth/reset/{token}",
        data={"password": "attacker-password", "confirm": "attacker-password"},
    )

    assert response.location.endswith("/auth/reset")
    db.session.refresh(user)
    assert user.check_password(PASSWORD)


def test_legacy_delete_endpoint_cannot_skip_email_code(client, user):
    """/profile/delete/final demands the emailed code; the old route must not bypass it."""
    login(client)

    client.post(
        "/profile/delete_account",
        data={"confirm_email": "test@example.com", "password": PASSWORD},
    )

    assert db.session.get(User, user.id) is not None


def test_premium_self_activation_is_off_by_default(app):
    from backend.config import Config

    assert Config.PREMIUM_SELF_ACTIVATION is False


# --- Horizontal access (BOLA) across nutrition resources ---------------------------------


def test_cannot_read_or_modify_other_users_product(client, user, victim):
    product = make_private_product(victim)
    login(client)

    assert client.get(f"/api/nutrition/products/{product.id}").status_code == 404
    assert (
        client.patch(f"/api/nutrition/products/{product.id}", json={"name": "pwned"}).status_code
        == 404
    )
    assert client.delete(f"/api/nutrition/products/{product.id}").status_code == 404
    assert (
        client.post(f"/api/nutrition/products/{product.id}/favorite", json={}).status_code == 404
    )
    search = client.get("/api/nutrition/products?q=secret").json["products"]
    assert all(p["id"] != product.id for p in search)


def test_cannot_log_other_users_private_product(client, user, victim):
    product = make_private_product(victim)
    meal = Meal(user_id=user.id, date=date.today(), name="lunch", category="lunch")
    db.session.add(meal)
    db.session.commit()
    login(client)

    single = client.post(
        "/api/nutrition/entries", json={"meal_id": meal.id, "product_id": product.id, "amount": 100}
    )
    bulk = client.post(
        "/api/nutrition/entries/bulk",
        json={"meal_id": meal.id, "items": [{"product_id": product.id, "amount": 100}]},
    )

    assert single.status_code in (400, 404)
    assert bulk.status_code in (400, 404)
    assert MealItem.query.filter_by(product_id=product.id).count() == 0


def test_cannot_move_entry_into_other_users_meal(client, user, victim):
    own_product = make_private_product(user, "mine")
    own_meal = Meal(user_id=user.id, date=date.today(), name="lunch", category="lunch")
    victim_meal = Meal(user_id=victim.id, date=date.today(), name="lunch", category="lunch")
    db.session.add_all([own_meal, victim_meal])
    db.session.commit()
    login(client)

    created = client.post(
        "/api/nutrition/entries",
        json={"meal_id": own_meal.id, "product_id": own_product.id, "amount": 100},
    )
    item_id = created.json["id"]

    response = client.patch(f"/api/nutrition/entries/{item_id}", json={"meal_id": victim_meal.id})

    assert response.status_code in (400, 404)
    assert db.session.get(MealItem, item_id).meal_id == own_meal.id


def test_cannot_touch_entries_in_other_users_meal(client, user, victim):
    product = make_private_product(victim)
    victim_meal = Meal(user_id=victim.id, date=date.today(), name="lunch", category="lunch")
    db.session.add(victim_meal)
    db.session.flush()
    item = MealItem(meal_id=victim_meal.id, product_id=product.id, name="secret", calories=1)
    db.session.add(item)
    db.session.commit()
    login(client)

    assert client.patch(f"/api/nutrition/entries/{item.id}", json={"amount": 1}).status_code == 404
    assert client.put(f"/api/nutrition/items/{item.id}", json={"amount": 1}).status_code == 404
    assert client.delete(f"/api/nutrition/entries/{item.id}").status_code == 404
    assert client.put(f"/api/nutrition/meals/{victim_meal.id}", json={}).status_code == 404
    assert db.session.get(MealItem, item.id) is not None


def test_cannot_log_or_remove_other_users_habit(client, user, victim):
    from backend.app.models.recovery.habit import RecoveryHabit
    from backend.app.models.recovery.user_habit import UserRecoveryHabit

    habit = RecoveryHabit(slug="walk", name="Walk", points=1)
    db.session.add(habit)
    db.session.flush()
    victim_habit = UserRecoveryHabit(user_id=victim.id, habit_id=habit.id)
    db.session.add(victim_habit)
    db.session.commit()
    login(client)

    assert client.post("/api/recovery/habits/logs", json={"user_habit_id": victim_habit.id}).status_code == 404
    assert client.delete(f"/api/recovery/habits/logs/{victim_habit.id}").status_code == 404
    assert client.delete(f"/api/recovery/habits/{victim_habit.id}").status_code == 404


# --- Malformed input should never reach the database as a crash ---------------------------


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("delete", "/api/nutrition/meals/99999999999", None),
        ("get", "/api/nutrition/products/99999999999", None),
        ("post", "/api/recovery/habits/add/99999999999", None),
        ("post", "/api/nutrition/entries", {"meal_id": "abc", "product_id": 1, "amount": 1}),
        ("post", "/api/nutrition/entries", {"meal_id": 99999999999, "product_id": 1, "amount": 1}),
        ("post", "/api/recovery/habits/logs", {"user_habit_id": 99999999999}),
        ("post", "/api/nutrition/products", {"name": ["not", "text"]}),
        ("post", "/api/nutrition/products", {"name": "x", "brand": "b" * 500}),
        ("get", "/api/recovery/heatmap/1?year=99999999", None),
        ("get", "/api/nutrition/heatmap?year=99999999", None),
    ],
)
def test_malformed_ids_and_values_are_client_errors(client, user, method, path, body):
    login(client)

    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)

    assert response.status_code < 500, response.get_data(as_text=True)


# --- Telegram bot ------------------------------------------------------------------------


def test_bot_only_serves_private_chats():
    from types import SimpleNamespace

    from telegram_bot.security import is_private_chat

    private = SimpleNamespace(chat=SimpleNamespace(type="private"))
    group = SimpleNamespace(chat=SimpleNamespace(type="group"))
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(type="supergroup")))

    assert is_private_chat(private)
    assert not is_private_chat(group)
    assert not is_private_chat(callback)


def test_bot_limits_login_attempts_per_telegram_user():
    from telegram_bot.security import LoginThrottle

    throttle = LoginThrottle(max_attempts=3, window_seconds=60)

    assert all(throttle.allow(42) for _ in range(3))
    assert not throttle.allow(42)
    assert throttle.allow(7)  # other users are not affected


def test_bot_ignores_login_attempts_in_groups():
    import asyncio
    from datetime import datetime

    from aiogram import Bot
    from aiogram.dispatcher.event.bases import UNHANDLED
    from aiogram.types import Chat, Message, Update, User as TgUser

    from telegram_bot.bot import create_dispatcher

    dispatcher = create_dispatcher()
    bot = Bot(token="123456:TEST-TOKEN-not-real-0000000000000")
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=-100, type="group"),
            from_user=TgUser(id=42, is_bot=False, first_name="A"),
            text="/login",
        ),
    )

    async def feed():
        try:
            return await dispatcher.feed_update(bot, update)
        finally:
            await bot.session.close()

    assert asyncio.run(feed()) is UNHANDLED


# --- CSRF / session / XSS / mass assignment probes ----------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "null"},
        {"Origin": "http://localhost.evil.example"},
        {"Origin": "http://evil.example", "Referer": "http://localhost/"},
        {"Origin": "https://localhost"},  # scheme differs
        {"Origin": "http://localhost:8080"},  # port differs
        {"Referer": "http://localhost@evil.example/"},
        {"Referer": "http://evil.example/?http://localhost/"},
    ],
)
def test_csrf_origin_check_bypass_attempts(client, user, headers):
    login(client)

    response = client.post("/api/nutrition/water", json={"amount": 1}, headers=headers)

    assert response.status_code == 403


def test_forged_session_for_another_user_is_rejected(client, user, victim):
    """Without SECRET_KEY an attacker cannot compute the password fingerprint."""
    with client.session_transaction() as session:
        session["_user_id"] = f"{victim.id}:{'0' * 32}"
        session["_fresh"] = True

    assert client.get("/profile/").status_code == 302


def test_username_is_escaped_in_html(client, user):
    login(client)
    client.post("/profile/update_full", data={"username": "<script>alert(1)</script>"})

    page = client.get("/profile/").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page


def test_plan_owner_cannot_be_overposted(client, user, victim):
    login(client)

    created = client.post(
        "/api/training/plans", json={"name": "p", "user_id": victim.id, "days": {}}
    ).json
    updated = client.put(
        f"/api/training/plans/{created['id']}", json={"user_id": victim.id, "id": 999}
    ).json

    assert created["user_id"] == user.id
    assert updated["user_id"] == user.id and updated["id"] == created["id"]


def test_profile_update_cannot_grant_premium(client, user):
    login(client)

    client.post("/profile/update_full", data={"username": "u", "is_premium": "1"})
    client.post("/api/onboarding/profile", json={"is_premium": True, "training_location": "gym"})

    db.session.refresh(user)
    assert not user.is_premium


def test_premium_activation_disabled(client, user, app):
    app.config["PREMIUM_SELF_ACTIVATION"] = False
    login(client)

    assert client.get("/premium/activate").status_code == 404
    db.session.refresh(user)
    assert not user.is_premium
