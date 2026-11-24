"""Quick entries through the bot and the real web app: food in three taps, sleep in two."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest
from aiogram.methods import EditMessageText, SendMessage

from backend.app.extensions import db
from backend.app.models.nutrition.meal_item import MealItem
from backend.app.models.recovery.sleep_entry import SleepEntry
from telegram_bot.handlers import quick
from telegram_bot.widgets.state import build_state
from web.tests.unit.test_nutrition_api import make_product
from web.tests.unit.test_telegram_training import catalog, tg  # noqa: F401  (fixtures)

KYIV = ZoneInfo("Europe/Kyiv")
MORNING = datetime(2026, 11, 24, 8, 10, tzinfo=KYIV)


def last_text(h):
    return [c for c in h.session.calls if isinstance(c, (SendMessage, EditMessageText))][-1].text


def buttons(h):
    markup = [c for c in h.session.calls if isinstance(c, (SendMessage, EditMessageText))][-1].reply_markup
    return [b.callback_data for row in markup.inline_keyboard for b in row]


@pytest.mark.parametrize(
    "bed, wake, start, end",
    [
        (time(23, 30), time(7, 0), "2026-11-23 23:30", "2026-11-24 07:00"),
        (time(0, 30), time(7, 30), "2026-11-24 00:30", "2026-11-24 07:30"),
        # A wake time still ahead today was this night's end yesterday morning.
        (time(23, 0), time(9, 0), "2026-11-22 23:00", "2026-11-23 09:00"),
    ],
)
def test_the_night_is_the_one_that_ended_last(bed, wake, start, end):
    got = quick.night(bed, wake, MORNING)

    assert [moment.strftime("%Y-%m-%d %H:%M") for moment in got] == [start, end]


def test_the_morning_card_asks_about_sleep_until_it_is_logged():
    # Not a brand-new account (that one is asked to start with one entry).
    habit = {"user_habit_id": 1, "slug": "", "name": "Walk", "completed": False}
    common = dict(day={"meals": []}, habits=[habit], session=None, stats=None, now=MORNING)
    asleep = {"date": "2026-11-24", "sleep_duration_minutes": 450}

    assert '"a":"sleep"' in build_state(snapshot=None, **common)
    assert '"a":"sleep"' not in build_state(snapshot=asleep, **common)


def test_sleep_in_two_taps(tg, monkeypatch):
    monkeypatch.setattr(quick, "local_now", lambda: datetime.now(KYIV).replace(hour=8, minute=10))

    tg.callback("sl:s")
    assert "sl:b:2330" in buttons(tg)
    tg.callback("sl:b:2330")
    assert "sl:w:2330:0700" in buttons(tg)
    tg.callback("sl:w:2330:0700")

    entry = SleepEntry.query.filter_by(user_id=tg.user.id).one()
    assert entry.duration_minutes == 450
    assert "7 год 30 хв" in last_text(tg)


def test_a_typed_bedtime_works_too(tg, monkeypatch):
    monkeypatch.setattr(quick, "local_now", lambda: datetime.now(KYIV).replace(hour=8, minute=10))

    tg.callback("sl:s")
    tg.message("23.15")
    tg.callback("sl:w:2315:0645")

    assert SleepEntry.query.filter_by(user_id=tg.user.id).one().duration_minutes == 450


def test_food_in_three_taps_and_undo(tg):
    product = make_product(kcal=124)
    assert tg.http.post(f"http://localhost/api/nutrition/products/{product.id}/favorite", json={"favorite": True}).ok

    tg.callback("qf:m:lunch")
    assert f"qf:p:{product.id}" in buttons(tg)
    tg.callback(f"qf:p:{product.id}")
    tg.callback("qf:a:150")

    item = MealItem.query.one()
    assert item.amount == 150
    assert "186 ккал" in last_text(tg)

    undo = next(data for data in buttons(tg) if data.startswith("qf:u:"))
    tg.callback(undo)
    db.session.expire_all()
    assert MealItem.query.count() == 0


def test_typing_a_name_searches_while_adding_food(tg):
    tg.callback("qf:m:dinner")
    tg.message("абвгдежзик")

    assert "нічого не знайшлося" in last_text(tg)
