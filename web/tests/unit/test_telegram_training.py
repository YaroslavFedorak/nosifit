"""🏋️ Тренування in the Telegram bot, end to end.

The bot runs through the real aiogram dispatcher (Telegram is recorded, see
test_telegram_bot.Harness) and talks to the real Flask API through the test
client: it signs in with the signed /api/telegram/login, so the Telegram
session scope and the API contract are exercised together with the UX.
"""

import asyncio
from urllib.parse import urlsplit

import pytest
import requests
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from requests.structures import CaseInsensitiveDict

from backend.app.extensions import db
from backend.app.models.telegram import TelegramIdentity
from backend.app.models.training_session import TrainingSession
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from telegram_bot import runtime
from telegram_bot.handlers import training as training_handlers
from telegram_bot.keyboards.main import (
    ADD_EXERCISE,
    FOOD,
    HOME,
    MY_WORKOUT,
    NUTRITION,
    TRAINING,
    WATER,
    WEIGHT,
)
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError
from web.tests.security.test_telegram_auth import SECRET, bot_post, tg_payload
from web.tests.security.test_telegram_bot import ALICE, Harness


class FlaskSession(requests.Session):
    """requests.Session that answers from the Flask test client."""

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.cookies.set("session", "flask-test-client")
        self.down = False

    def request(self, method, url, params=None, json=None, timeout=None, allow_redirects=True, **kwargs):
        if self.down:
            raise requests.ConnectionError("down")
        flask_response = self.client.open(
            urlsplit(url).path, method=method, query_string=params, json=json
        )
        response = requests.Response()
        response.status_code = flask_response.status_code
        response._content = flask_response.get_data()
        response.headers = CaseInsensitiveDict(dict(flask_response.headers))
        response.url = url
        response.reason = flask_response.status
        return response


@pytest.fixture
def catalog(app):
    rows = {}
    for item in load_exercise_catalog():
        exercise = Exercise(**item)
        db.session.add(exercise)
        rows[item["slug"]] = exercise
    db.session.commit()
    return rows


@pytest.fixture
def tg(app, client, user, catalog, monkeypatch):
    """Alice's Telegram is linked to ``user`` and signed in through the bot."""
    app.config["TELEGRAM_BOT_API_SECRET"] = SECRET
    app.config["PUBLIC_BASE_URL"] = "http://localhost"
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=ALICE.id, telegram_username="alice_tg"))
    db.session.commit()
    assert bot_post(client, "/api/telegram/login", tg_payload(ALICE.id)).status_code == 200

    from flask import g

    def forget_cached_user():
        # Must return None: a before_request value is taken as the response.
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)

    async def in_this_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    # One thread: the Flask test client and the test share the app context.
    monkeypatch.setattr(asyncio, "to_thread", in_this_thread)

    session = FlaskSession(client)
    runtime._sessions.clear()
    runtime._sessions[ALICE.id] = NosiFitAPI(base_url="http://localhost", session=session)
    training_handlers._locks.clear()
    harness = Harness()
    harness.http = session
    harness.user = user
    yield harness
    harness.close()
    runtime._sessions.clear()


# --- helpers ---------------------------------------------------------------------------


def screens(h):
    return [c for c in h.session.calls if isinstance(c, (SendMessage, EditMessageText))]


def screen(h):
    return screens(h)[-1]


def text(h):
    return screen(h).text


def buttons(h):
    markup = screen(h).reply_markup
    rows = getattr(markup, "inline_keyboard", None) or []
    return [button for row in rows for button in row]


def button(h, label):
    """The button labelled exactly ``label``, else the first containing it."""
    found = [b for b in buttons(h) if b.text == label] or [b for b in buttons(h) if label in b.text]
    assert found, f"no button {label!r} in {[b.text for b in buttons(h)]}"
    return found[0]


def press(h, label):
    data = button(h, label).callback_data
    h.callback(data)
    return data


def toasts(h):
    return [c.text for c in h.session.calls if isinstance(c, AnswerCallbackQuery) and c.text]


def sessions(h):
    db.session.expire_all()
    return TrainingSession.query.filter_by(user_id=h.user.id).all()


def only_session(h):
    found = sessions(h)
    assert len(found) == 1
    return found[0]


def rows_by_slug(session, catalog):
    by_id = {exercise.id: slug for slug, exercise in catalog.items()}
    return {by_id[row.exercise_id]: row for row in session.exercises}


def reply_keyboard(h):
    """Texts of the last reply keyboard (the mode buttons)."""
    for call in reversed(screens(h)):
        rows = getattr(call.reply_markup, "keyboard", None)
        if rows:
            return [[b.text for b in row] for row in rows]
    return None


def save_on_server(h, catalog, items, session_id=None):
    payload = [{"exercise": {"id": catalog[slug].id}, **values} for slug, values in items]
    body = {"exercises": payload, "session_id": session_id}
    return h.http.request("POST", "http://localhost/api/training/sessions/complete", json=body).json()


def log_set(h, query, name, *answers):
    """➕ Додати вправу → search → pick → weight/reps answers."""
    h.message(ADD_EXERCISE)
    h.message(query)
    press(h, name)
    for answer in answers:
        h.message(answer)


# --- the main scenario -------------------------------------------------------------------


def test_new_user_logs_a_workout_step_by_step(tg, catalog):
    tg.message(TRAINING)
    assert "Ще немає вправ" in text(tg)
    assert reply_keyboard(tg) == [[ADD_EXERCISE, MY_WORKOUT], [HOME]]

    tg.message(ADD_EXERCISE)
    assert "Напишіть назву вправи" in text(tg)
    tg.message("жим")
    press(tg, "Жим штанги лежачи")
    assert "Яка вага, кг?" in text(tg)
    tg.message("60")
    assert "Скільки повторів?" in text(tg)
    tg.message("10")
    assert "✅ Підхід записано" in text(tg)
    assert "Жим штанги лежачи</b>: 1 підхід · 60 кг × 10" in text(tg)

    press(tg, "➕ Ще підхід")
    assert "2 підходи · 60 кг × 10" in text(tg)
    press(tg, "✅ Готово")
    assert "1. Жим штанги лежачи — 2 підходи · 60 кг × 10" in text(tg)

    log_set(tg, "планка", "Планка")
    assert "Скільки секунд?" in text(tg)
    tg.message("45")
    assert "Планка</b>: 1 підхід · 45 с" in text(tg)

    tg.message(MY_WORKOUT)
    assert "Всього: 2 вправи · 3 підходи" in text(tg)
    press(tg, "✅ Завершити тренування")
    assert "Завершити тренування?" in text(tg)
    press(tg, "✅ Завершити")
    assert "Тренування збережено" in text(tg) and "2 вправи · 3 підходи" in text(tg)

    rows = rows_by_slug(only_session(tg), catalog)
    bench, plank = rows["bench-press"], rows["plank"]
    assert (bench.sets_done, bench.reps_done, bench.load_done) == (2, "10", 60.0)
    assert (plank.sets_done, plank.duration_sec_done) == (1, 45)


def test_bodyweight_exercise_asks_only_reps_and_offers_last_time(tg, catalog):
    import datetime as dt

    from backend.app.models.training_session import SessionExercise

    when = dt.datetime.utcnow() - dt.timedelta(days=2)
    past = TrainingSession(user_id=tg.user.id, status="finished", started_at=when, finished_at=when)
    db.session.add(past)
    db.session.flush()
    db.session.add(SessionExercise(session_id=past.id, exercise_id=catalog["push-ups"].id, sets_done=3, reps_done="33"))
    db.session.commit()

    tg.message(ADD_EXERCISE)
    press(tg, "Віджимання")  # recent, one tap
    assert "Минулого разу: 3 підходи · × 33" in text(tg)
    assert "Скільки повторів?" in text(tg)
    press(tg, "33 повт.")
    assert "Віджимання</b>: 1 підхід · × 33" in text(tg)


def test_double_tap_on_one_more_set_adds_one(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "60", "10")
    data = button(tg, "➕ Ще підхід").callback_data
    tg.callback(data)
    tg.callback(data)
    assert "Цей підхід уже записано." in toasts(tg)
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


# --- full sync with the server ---------------------------------------------------------------


def test_bot_never_drops_exercises_logged_on_the_website(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "60", "10")
    session_id = only_session(tg).id
    # The website saves the same session with one more exercise.
    save_on_server(
        tg,
        catalog,
        [("bench-press", {"sets": 1, "reps": 10, "load": 60}), ("lat-pulldown", {"sets": 3, "reps": 12, "load": 45})],
        session_id,
    )
    press(tg, "➕ Ще підхід")  # the bot's screen is from before that save

    rows = rows_by_slug(only_session(tg), catalog)
    assert set(rows) == {"bench-press", "lat-pulldown"}
    assert rows["bench-press"].sets_done == 2


# --- editing ----------------------------------------------------------------------------------


def test_edit_remove_set_and_delete(tg, catalog):
    save_on_server(
        tg,
        catalog,
        [("bench-press", {"sets": 3, "reps": 10, "load": 60, "rpe": 8}), ("plank", {"sets": 2, "duration_sec": 60})],
    )
    tg.message(MY_WORKOUT)
    press(tg, "1. Жим штанги лежачи")
    assert "Сьогодні: 3 підходи · 60 кг × 10" in text(tg)
    press(tg, "➖ Прибрати підхід")
    assert "Сьогодні: 2 підходи" in text(tg)

    press(tg, "✏️ Змінити")
    assert "Зараз: 2 підходи · 60 кг × 10" in text(tg)
    tg.message("62,5")
    tg.message("8")
    assert "✅ Змінено" in text(tg) and "2 підходи · 62,5 кг × 8" in text(tg)
    bench = rows_by_slug(only_session(tg), catalog)["bench-press"]
    assert (bench.sets_done, bench.reps_done, bench.load_done, bench.rpe) == (2, "8", 62.5, 8.0)

    press(tg, "🗑 Видалити")
    press(tg, "🗑 Видалити")
    assert "1. Планка" in text(tg) and "Жим" not in text(tg)

    press(tg, "1. Планка")
    press(tg, "🗑 Видалити")
    press(tg, "🗑 Видалити")
    assert "Ще немає вправ" in text(tg)
    assert sessions(tg) == []  # no empty session is left


def test_invalid_answers_are_explained(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "багато")
    assert "Напишіть вагу числом" in text(tg)
    tg.message("60")
    tg.message("8,5")
    assert "ціле число повторів" in text(tg)
    assert sessions(tg) == []


# --- navigation and errors ---------------------------------------------------------------------


def test_modes_and_home(tg, catalog):
    tg.message(NUTRITION)
    assert reply_keyboard(tg) == [[FOOD, WATER, WEIGHT], [HOME]]
    tg.message(TRAINING)
    assert reply_keyboard(tg) == [[ADD_EXERCISE, MY_WORKOUT], [HOME]]
    tg.message(ADD_EXERCISE)
    tg.message(HOME)  # also leaves the search step
    assert reply_keyboard(tg) == [[TRAINING, NUTRITION], ["🚪 Вийти"]]
    tg.message("жим")
    assert "Оберіть вправу" not in text(tg)


def test_cancel_keeps_what_is_logged(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "60", "10")
    tg.message(ADD_EXERCISE)
    tg.message("/cancel")
    assert "Скасовано. Усе записане збережено." in text(tg)
    assert len(sessions(tg)) == 1


def test_search_without_results(tg, catalog):
    tg.message(ADD_EXERCISE)
    tg.message("xyzqqq")
    assert "нічого не знайдено" in text(tg)


def test_network_error_is_human(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "60", "10")
    tg.http.down = True
    press(tg, "➕ Ще підхід")
    assert "Не вдалося підключитися до NosiFit." in toasts(tg)
    tg.http.down = False
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 1


def test_signed_out_user_is_asked_to_sign_in(tg, catalog):
    runtime._sessions.clear()
    tg.message(TRAINING)
    assert "Спочатку увійдіть" in text(tg)
