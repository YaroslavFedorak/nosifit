import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from telegram_bot import i18n
from telegram_bot.handlers import today
from telegram_bot.services.widget_api import AnswerWidgetQuery, EditMessageWidgetData
from telegram_bot.widgets.render import MAX_COMPRESSED, compressed_size, today_html
from telegram_bot.widgets.state import MAX_STATE, build_state

KYIV = ZoneInfo("Europe/Kyiv")
LUNCHTIME = datetime(2026, 11, 23, 13, 40, tzinfo=KYIV)
EMPTY = dict(day={"meals": [], "water": 0}, snapshot=None, habits=[], session=None, stats=None)


@pytest.fixture
def uk():
    token = i18n.use_language(0, "uk")
    yield
    i18n.reset_language(token)


def state(**parts):
    return json.loads(build_state(**{**EMPTY, "now": LUNCHTIME, **parts}))


@pytest.mark.parametrize("language", list(i18n.LANGUAGES))
def test_the_card_fits_telegrams_size_limit_in_every_language(language):
    page = today_html(language)

    assert compressed_size(page) <= MAX_COMPRESSED
    assert "{{" not in page and "/*" not in page


def test_nothing_recorded_is_left_out_not_shown_as_zero(uk):
    card = state()

    assert not {"f", "w", "s", "t", "k", "h"} & card.keys()
    assert card["n"] == i18n.t("w.next.start")


def test_the_next_step_asks_for_the_meal_of_the_hour(uk):
    breakfast = {"meals": [{"category": "breakfast", "items": [1]}], "kcal": 400, "water": 0}

    assert state(day=breakfast)["n"] == i18n.t("w.next.lunch")


def test_sleep_of_an_earlier_night_is_not_todays(uk):
    old = {"date": "2026-11-22", "sleep_duration_minutes": 420}
    tonight = {**old, "date": "2026-11-23", "sleep_start": "2026-11-22T21:40:00Z", "sleep_end": "2026-11-23T05:00:00Z"}

    assert "s" not in state(snapshot=old)
    assert state(snapshot=tonight)["s"] == ["7 год 0 хв", "23:40–07:00"]


def test_many_long_habits_still_fit_the_chat_state(uk):
    habits = [
        {"user_habit_id": i, "slug": "", "name": "Дуже довга назва звички " * 4, "completed": i % 2 == 0}
        for i in range(40)
    ]

    text = build_state(**{**EMPTY, "habits": habits, "now": LUNCHTIME})

    assert len(text.encode("utf-8")) <= MAX_STATE
    card = json.loads(text)
    assert card["hn"] == 40 and 0 < len(card["h"]) <= 6


class FakeAPI:
    def __init__(self):
        self.water = []
        self.habits = [{"user_habit_id": 7, "slug": "drink_water", "name": "Water", "completed": False}]

    def add_water(self, liters):
        self.water.append(liters)

    def get_habits(self):
        return self.habits

    def set_habit(self, habit_id, done):
        self.habits[0]["completed"] = done

    def get_day(self):
        return {"meals": [], "water": sum(self.water), "water_goal": 2.5}

    def get_snapshot(self):
        return None

    def get_today_session(self):
        return None

    def get_stats(self, days):
        return None


class RecordingBot:
    def __init__(self):
        self.calls = []

    async def __call__(self, method):
        self.calls.append(method)
        return True


def query(data, chat_type="private", user_id=111):
    return {
        "id": "q1",
        "from": {"id": user_id, "is_bot": False, "first_name": "A", "language_code": "uk"},
        "chat": {"id": user_id, "type": chat_type},
        "message_id": 55,
        "chat_instance": "ci",
        "data": data,
    }


@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(today, "restore", lambda user_id: fake)
    today._shown.clear()
    return fake


def run(bot, data, **kwargs):
    asyncio.run(today.answer_widget_query(bot, query(data, **kwargs)))


def test_a_tap_on_water_logs_it_and_redraws_the_card(api):
    bot = RecordingBot()

    run(bot, "w250")

    assert api.water == [0.25]
    answer, edit = bot.calls
    assert isinstance(answer, AnswerWidgetQuery) and json.loads(answer.data)["w"][0] == "0.25 з 2.5 л"
    assert isinstance(edit, EditMessageWidgetData) and (edit.chat_id, edit.message_id) == (111, 55)


def test_a_tap_on_a_habit_ticks_it(api):
    run(RecordingBot(), "h7")

    assert api.habits[0]["completed"] is True


def test_a_refresh_with_nothing_new_does_not_edit_the_message(api):
    bot = RecordingBot()

    run(bot, "r")
    run(bot, "r")

    assert [type(call) for call in bot.calls] == [AnswerWidgetQuery, EditMessageWidgetData, AnswerWidgetQuery]


def test_a_failed_tap_answers_without_state(api):
    bot = RecordingBot()

    run(bot, "h999")

    assert [(type(call), call.data) for call in bot.calls] == [(AnswerWidgetQuery, None)]


def test_cards_outside_the_private_chat_change_nothing(api):
    bot = RecordingBot()

    run(bot, "w500", chat_type="group")

    assert api.water == []
    assert [(type(call), call.data) for call in bot.calls] == [(AnswerWidgetQuery, None)]


@pytest.mark.parametrize(
    "step, first",
    [("sleep", "sl:s"), ("lunch", "qf:m:lunch"), ("done", "qf:m:auto"), (None, "qf:m:auto")],
)
def test_the_first_button_under_the_card_is_the_steps_own(uk, step, first):
    assert today.card_keyboard(step).inline_keyboard[0][0].callback_data == first
