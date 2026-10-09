"""🍽 Харчування in the Telegram bot, end to end: search, dishes, snapshots.

Same setup as test_telegram_training: the real aiogram dispatcher talks to
the real Flask API through the test client. Every HTTP request the bot makes
is counted, so the "one request per action" promises are tested too.
"""

import asyncio
from datetime import date

import pytest

from backend.app.extensions import db
from backend.app.models import Dish, Meal, MealItem, Product, ProductName
from backend.app.models.telegram import TelegramIdentity
from telegram_bot import runtime
from telegram_bot.services.api import NosiFitAPI
from web.tests.security.test_telegram_auth import SECRET, bot_post, tg_payload
from web.tests.security.test_telegram_bot import ALICE, Harness
from web.tests.unit.test_telegram_training import FlaskSession, button, buttons, press, text, toasts


class CountingSession(FlaskSession):
    def __init__(self, client):
        super().__init__(client)
        self.requests = []

    def request(self, method, url, *args, **kwargs):
        if not self.down:
            self.requests.append((method, url.split("localhost", 1)[-1]))
        return super().request(method, url, *args, **kwargs)


def product(uk, kcal, protein=0.0, fat=0.0, carbs=0.0, sugar=0.0, fiber=0.0, unit="g", gpu=1.0):
    row = Product(
        source="system", category="other", kcal_per_100g=kcal, protein_per_100g=protein,
        fat_per_100g=fat, carbs_per_100g=carbs, sugar_per_100g=sugar, fiber_per_100g=fiber,
        default_unit=unit, grams_per_unit=gpu, liquid_ml_per_100g=0,
    )
    row.names = [ProductName(locale="uk", name=uk)]
    db.session.add(row)
    return row


@pytest.fixture
def food(app):
    rows = {
        "chicken": product("Куряче філе", 110, protein=23.4, fat=1.5),
        "chicken_roasted": product("Куряче філе запечене", 165, protein=31, fat=3.6),
        "oats": product("Вівсянка", 370, protein=11, fat=7.7, carbs=58, sugar=1.8, fiber=10.6),
        "milk": product("Молоко 2,5%", 55, protein=3.4, fat=2.5, carbs=4.8, sugar=4.5, unit="ml", gpu=1.03),
        "banana": product("Банан", 90, protein=1, carbs=20, sugar=15.6, fiber=2.7),
        "apple": product("Яблуко", 52, carbs=12, sugar=9.4, fiber=1.4),
    }
    db.session.commit()
    return rows


@pytest.fixture
def tg(app, client, user, food, monkeypatch):
    app.config["TELEGRAM_BOT_API_SECRET"] = SECRET
    app.config["PUBLIC_BASE_URL"] = "http://localhost"
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=ALICE.id, telegram_username="alice_tg"))
    db.session.commit()
    assert bot_post(client, "/api/telegram/login", tg_payload(ALICE.id)).status_code == 200

    from flask import g

    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)

    async def in_this_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", in_this_thread)

    session = CountingSession(client)
    runtime._sessions.clear()
    runtime._sessions[ALICE.id] = NosiFitAPI(base_url="http://localhost", session=session)
    harness = Harness()
    harness.http = session
    harness.user = user
    harness.food = food
    yield harness
    harness.close()
    runtime._sessions.clear()


@pytest.fixture
def oatmeal(tg, food):
    response = tg.http.request("POST", "http://localhost/api/nutrition/dishes", json={
        "name": "Моя вівсянка",
        "items": [
            {"product_id": food["oats"].id, "amount": 80, "unit": "g"},
            {"product_id": food["milk"].id, "amount": 250, "unit": "ml"},
            {"product_id": food["banana"].id, "amount": 120, "unit": "g"},
        ],
    })
    assert response.status_code == 201
    return response.json()


def entries(h):
    db.session.expire_all()
    return (
        MealItem.query.join(Meal)
        .filter(Meal.user_id == h.user.id, Meal.date == date.today())
        .order_by(MealItem.id)
        .all()
    )


def start_breakfast(h):
    """➕ Додати їжу → Сніданок → no time."""
    h.callback("nutrition:add")
    h.callback("nutrition:meal:breakfast")
    press(h, "Пропустити")


def requests_during(h, action):
    before = len(h.http.requests)
    action()
    return h.http.requests[before:]


# --- search ----------------------------------------------------------------------


def test_typo_search_finds_the_product_in_one_request(tg):
    start_breakfast(tg)
    sent = requests_during(tg, lambda: tg.message("куряче фле"))
    assert [method for method, _ in sent] == ["GET"]
    assert sent[0][1].startswith("/api/nutrition/products")
    labels = [b.text for b in buttons(tg)]
    assert labels[0] == "Куряче філе"
    assert "Куряче філе запечене" in labels


def test_adding_a_product_saves_in_one_request(tg):
    start_breakfast(tg)
    tg.message("куряче філе")
    press(tg, "Куряче філе")
    tg.message("150")
    assert "Підсумок чернетки" in text(tg)
    sent = requests_during(tg, lambda: press(tg, "Зберегти"))
    assert sent == [("POST", "/api/nutrition/log")]
    assert "Прийом їжі збережено" in text(tg)
    assert [(e.name, e.amount, e.calories) for e in entries(tg)] == [("Куряче філе", 150, 165)]


# --- dishes ---------------------------------------------------------------------


def test_dish_preview_and_add_as_saved(tg, oatmeal):
    start_breakfast(tg)
    press(tg, "Мої страви")
    assert "Моя вівсянка" in button(tg, "Моя вівсянка").text

    # The preview comes from the list already loaded: no request.
    sent = requests_during(tg, lambda: press(tg, "Моя вівсянка"))
    assert sent == []
    preview = text(tg)
    assert "Вівсянка — 80 г" in preview and "Молоко 2,5% — 250 мл" in preview and "Банан — 120 г" in preview

    sent = requests_during(tg, lambda: press(tg, "Додати"))
    assert sent == [("POST", "/api/nutrition/log")]
    assert "Моя вівсянка" in text(tg) and "додано" in text(tg)
    logged = entries(tg)
    assert [(e.name, e.amount, e.dish_id) for e in logged] == [
        ("Вівсянка", 80, oatmeal["id"]),
        ("Молоко 2,5%", 250, oatmeal["id"]),
        ("Банан", 120, oatmeal["id"]),
    ]


def test_edit_dish_for_this_meal_only(tg, oatmeal, food):
    start_breakfast(tg)
    press(tg, "Мої страви")
    press(tg, "Моя вівсянка")
    press(tg, "Змінити")
    assert "зміни стосуються лише цього прийому" in text(tg)

    # Less milk.
    press(tg, "✏️ Молоко")
    tg.message("200")
    # Banana → apple.
    tg.callback("nutrition:replace:2")
    tg.message("яблуко")
    press(tg, "Яблуко")
    tg.message("150")
    draft = text(tg)
    assert "Молоко 2,5% — 200 мл" in draft and "Яблуко — 150 г" in draft and "Банан" not in draft

    sent = requests_during(tg, lambda: press(tg, "Зберегти"))
    assert sent == [("POST", "/api/nutrition/log")]
    assert [(e.name, e.amount) for e in entries(tg)] == [
        ("Вівсянка", 80), ("Молоко 2,5%", 200), ("Яблуко", 150),
    ]
    assert {e.dish_id for e in entries(tg)} == {oatmeal["id"]}

    # The template did not change.
    db.session.expire_all()
    dish = db.session.get(Dish, oatmeal["id"])
    assert [(i.product_id, i.amount) for i in dish.items] == [
        (food["oats"].id, 80), (food["milk"].id, 250), (food["banana"].id, 120),
    ]
    assert dish.use_count == 1


def test_update_template_from_the_draft(tg, oatmeal, food):
    start_breakfast(tg)
    press(tg, "Мої страви")
    press(tg, "Моя вівсянка")
    press(tg, "Змінити")
    press(tg, "🗑")  # remove oats from the draft
    press(tg, "Оновити")
    assert "♻️ Страву оновлено" in toasts(tg)
    db.session.expire_all()
    assert [i.product_id for i in db.session.get(Dish, oatmeal["id"]).items] == [
        food["milk"].id, food["banana"].id,
    ]


def test_save_draft_as_a_new_dish(tg, food):
    start_breakfast(tg)
    tg.message("банан")
    press(tg, "Банан")
    tg.message("120")
    press(tg, "Зберегти як страву")
    tg.message("Банановий перекус")
    assert any("збережено" in t for t in tg.texts())
    dish = Dish.query.filter_by(user_id=tg.user.id).one()
    assert dish.name == "Банановий перекус"
    assert [(i.product_id, i.amount) for i in dish.items] == [(food["banana"].id, 120)]


def test_dish_from_main_menu_asks_for_the_meal(tg, oatmeal):
    tg.callback("nutrition:dishes")
    press(tg, "Моя вівсянка")
    press(tg, "Додати")
    assert "До якого прийому їжі" in text(tg)
    tg.callback("nutrition:meal:snack")
    press(tg, "Пропустити")
    assert "Підсумок чернетки" in text(tg)
    press(tg, "Зберегти")
    assert len(entries(tg)) == 3


def test_delete_dish(tg, oatmeal):
    tg.callback("nutrition:dishes")
    press(tg, "Моя вівсянка")
    press(tg, "Видалити страву")
    press(tg, "Так, видалити")
    assert Dish.query.count() == 0
    assert "поки немає" in text(tg)


# --- own products: unknown stays unknown --------------------------------------


def test_own_product_with_skipped_sugar_and_fiber(tg):
    tg.callback("nutrition:my-product")
    tg.message("Домашня гранола")
    press(tg, "Без бренду")
    for value in ("450", "10", "20", "55"):
        tg.message(value)
    assert "цукру" in tg.texts()[-1]
    press(tg, "пропустити")
    press(tg, "пропустити")
    created = Product.query.filter_by(owner_user_id=tg.user.id).one()
    assert created.sugar_per_100g is None and created.fiber_per_100g is None
    assert "Цукор: —" in text(tg) and "Клітковина: —" in text(tg)


# --- errors -----------------------------------------------------------------------


def test_save_failure_keeps_the_draft(tg):
    start_breakfast(tg)
    tg.message("банан")
    press(tg, "Банан")
    tg.message("100")
    tg.http.down = True
    press(tg, "Зберегти")
    assert "Чернетку збережено" in tg.texts()[-1]
    tg.http.down = False
    tg.callback("nutrition:save")  # the review buttons are still on screen
    assert [(e.name, e.amount) for e in entries(tg)] == [("Банан", 100)]


def test_duplicate_dish_name_is_explained(tg, oatmeal):
    start_breakfast(tg)
    tg.message("банан")
    press(tg, "Банан")
    tg.message("100")
    press(tg, "Зберегти як страву")
    tg.message("моя вівсянка")
    assert "уже є страва з такою назвою" in tg.texts()[-1]
