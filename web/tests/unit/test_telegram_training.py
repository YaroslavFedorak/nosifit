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
    """➕ Додати вправу → search → pick → answers (sets, then reps/kg per set)."""
    h.message(ADD_EXERCISE)
    h.message(query)
    press(h, name)
    for answer in answers:
        h.message(answer)


# --- the main scenario -------------------------------------------------------------------


def test_sets_with_their_own_reps_and_weight(tg, catalog):
    tg.message(TRAINING)
    assert reply_keyboard(tg) == [[ADD_EXERCISE, MY_WORKOUT], [HOME]]

    tg.message(ADD_EXERCISE)
    tg.message("жим штанги лежачи")
    press(tg, "Жим штанги лежачи")
    assert "Скільки підходів?" in text(tg)
    press(tg, "3")
    assert "підхід 1 з 3" in text(tg) and "Скільки повторів?" in text(tg)
    tg.message("12")
    assert "Яка вага, кг?" in text(tg)
    tg.message("60")
    assert "підхід 2 з 3" in text(tg)
    tg.message("11")
    tg.message("55")
    tg.message("8")
    tg.message("50")
    assert "✅ Записано" in text(tg)
    assert "1. 12 × 60 кг\n2. 11 × 55 кг\n3. 8 × 50 кг" in text(tg)

    row = rows_by_slug(only_session(tg), catalog)["bench-press"]
    assert row.set_entries == [{"reps": 12, "load": 60.0}, {"reps": 11, "load": 55.0}, {"reps": 8, "load": 50.0}]
    assert row.sets_done == 3

    press(tg, "➕ Ще підхід")
    assert "Скільки повторів?" in text(tg)
    press(tg, "↻")  # like the previous set: 8 × 50 кг
    assert "4. 8 × 50 кг" in text(tg)

    press(tg, "✅ Готово")
    assert "Жим штанги лежачи</b> — 4 підходи: 12×60 · 11×55 · 8×50 · 8×50 кг" in text(tg)
    press(tg, "✅ Завершити тренування")
    press(tg, "✅ Завершити")
    assert "1 вправа · 4 підходи" in text(tg)


def test_like_previous_set_fills_the_whole_set(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи")
    press(tg, "2")
    tg.message("10")
    tg.message("60")
    press(tg, "↻ Як попередній")
    assert "1. 10 × 60 кг\n2. 10 × 60 кг" in text(tg)


def test_bodyweight_and_duration_skip_the_weight(tg, catalog):
    log_set(tg, "віджимання", "Віджимання")
    press(tg, "2")
    tg.message("20")
    assert "підхід 2 з 2" in text(tg)
    tg.message("15")
    assert "1. 20 повт.\n2. 15 повт." in text(tg)

    log_set(tg, "планка", "Планка")
    press(tg, "1")
    assert "Скільки секунд?" in text(tg)
    tg.message("45")
    assert "1. 45 с" in text(tg)


def test_last_time_is_offered(tg, catalog):
    import datetime as dt

    from backend.app.models.training_session import SessionExercise

    when = dt.datetime.utcnow() - dt.timedelta(days=2)
    past = TrainingSession(user_id=tg.user.id, status="finished", started_at=when, finished_at=when)
    db.session.add(past)
    db.session.flush()
    db.session.add(SessionExercise(
        session_id=past.id, exercise_id=catalog["bench-press"].id, sets_done=2, reps_done="10", load_done=55,
        set_entries=[{"reps": 12, "load": 60}, {"reps": 8, "load": 50}],
    ))
    db.session.commit()

    tg.message(ADD_EXERCISE)
    press(tg, "Жим штанги лежачи")  # recent
    assert "Минулого разу: 2 підходи: 12×60 · 8×50 кг" in text(tg)
    assert button(tg, "2").text == "• 2"
    press(tg, "• 2")
    press(tg, "↻ Як минулого разу")
    press(tg, "↻ Як минулого разу")  # set 2 of last time
    assert "1. 12 × 60 кг\n2. 8 × 50 кг" in text(tg)


# --- full sync with the server ---------------------------------------------------------------


def test_bot_never_drops_exercises_logged_on_the_website(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "1", "10", "60")
    session_id = only_session(tg).id
    save_on_server(
        tg,
        catalog,
        [("bench-press", {"sets": 1, "reps": 10, "load": 60}), ("lat-pulldown", {"sets": 3, "reps": 12, "load": 45})],
        session_id,
    )
    press(tg, "➕ Ще підхід")
    tg.message("9")
    tg.message("60")

    rows = rows_by_slug(only_session(tg), catalog)
    assert set(rows) == {"bench-press", "lat-pulldown"}
    assert rows["bench-press"].sets_done == 2


# --- editing ----------------------------------------------------------------------------------


def test_remove_last_set_redo_and_delete(tg, catalog):
    save_on_server(
        tg,
        catalog,
        [("bench-press", {"sets": 3, "reps": 10, "load": 60, "rpe": 8}), ("plank", {"sets": 2, "duration_sec": 60})],
    )
    tg.message(MY_WORKOUT)
    press(tg, "1. Жим штанги лежачи")
    assert "1. 10 × 60 кг\n2. 10 × 60 кг\n3. 10 × 60 кг" in text(tg)
    data = button(tg, "➖ Останній підхід").callback_data
    tg.callback(data)
    tg.callback(data)  # the same screen pressed again
    assert "Цей підхід уже прибрано." in toasts(tg)
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2

    press(tg, "✏️ Ввести заново")
    assert "Зараз: 2 підходи" in text(tg)
    press(tg, "1")
    tg.message("5")
    tg.message("100")
    assert "✅ Записано" in text(tg) and "1. 5 × 100 кг" in text(tg)
    bench = rows_by_slug(only_session(tg), catalog)["bench-press"]
    assert (bench.sets_done, bench.load_done, bench.rpe) == (1, 100.0, 8.0)

    press(tg, "✅ Готово")
    press(tg, "1. Жим штанги лежачи")
    press(tg, "🗑 Видалити")
    press(tg, "🗑 Видалити")
    assert "1. <b>Планка</b>" in text(tg)
    press(tg, "1. Планка")
    press(tg, "🗑 Видалити")
    press(tg, "🗑 Видалити")
    assert "Ще немає вправ" in text(tg)
    assert sessions(tg) == []


def test_invalid_answers_are_explained(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "багато")
    assert "кількість підходів" in text(tg)
    tg.message("1")
    tg.message("8,5")
    assert "ціле число повторів" in text(tg)
    tg.message("8")
    tg.message("важко")
    assert "Напишіть вагу числом" in text(tg)
    assert sessions(tg) == []


# --- navigation and errors ---------------------------------------------------------------------


def test_modes_and_home(tg, catalog):
    tg.message(NUTRITION)
    assert reply_keyboard(tg) == [[FOOD, WATER, WEIGHT], [HOME]]
    tg.message(ADD_EXERCISE)
    tg.message(HOME)
    assert reply_keyboard(tg) == [[TRAINING, NUTRITION], ["🚪 Вийти"]]
    tg.message("жим")
    assert "Оберіть вправу" not in text(tg)


def test_cancel_keeps_what_is_logged(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "1", "10", "60")
    log_set(tg, "планка", "Планка")
    tg.message("/cancel")
    assert "Скасовано. Усе записане збережено." in text(tg)
    assert len(only_session(tg).exercises) == 1


def test_network_error_is_human(tg, catalog):
    log_set(tg, "жим штанги лежачи", "Жим штанги лежачи", "1", "10")
    tg.http.down = True
    tg.message("60")
    assert text(tg) == "Не вдалося підключитися до NosiFit."
    tg.http.down = False
    assert sessions(tg) == []


def test_signed_out_user_is_asked_to_sign_in(tg, catalog):
    runtime._sessions.clear()
    tg.message(TRAINING)
    assert "Спочатку увійдіть" in text(tg)
