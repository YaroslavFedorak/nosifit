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
from telegram_bot.keyboards.main import NUTRITION, TRAINING
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


def open_new_exercise(h, query, name):
    h.message(query)
    press(h, name)
    assert "ще немає підходів" in text(h)


# --- main scenario: a new user logs a workout ---------------------------------------------


def test_new_user_logs_a_whole_workout(tg, catalog):
    tg.message(TRAINING)
    assert "Сьогодні ще немає вправ" in text(tg)
    assert [b.text for b in buttons(tg)] == ["❌ Скасувати"]

    tg.message("жим")
    assert "Оберіть вправу" in text(tg)
    assert any("Жим штанги лежачи" in b.text for b in buttons(tg))

    press(tg, "Жим штанги лежачи")
    assert "Сьогодні: ще немає підходів" in text(tg)
    assert sessions(tg) == []  # opening an exercise logs nothing

    tg.message("60 10 2")
    assert "Сьогодні: 1 × 10 · 60 кг · RIR 2" in text(tg)
    press(tg, "➕ Підхід")
    press(tg, "➕ Підхід")
    assert "Сьогодні: 3 × 10 · 60 кг · RIR 2" in text(tg)

    open_new_exercise(tg, "присідання зі штангою на спині", "Присідання зі штангою на спині")
    tg.message("80 8")
    press(tg, "← Тренування")

    home = text(tg)
    assert "1. Жим штанги лежачи — 3 × 10 · 60 кг · RIR 2" in home
    assert "2. Присідання зі штангою на спині — 1 × 8 · 80 кг" in home
    assert "Всього: 2 вправи · 4 підходи" in home

    press(tg, "✅ Завершити")
    assert "Завершити тренування?" in text(tg) and "4 підходи · 2 вправи" in text(tg)
    press(tg, "✅ Завершити")
    assert "Тренування збережено" in text(tg) and "2 вправи · 4 підходи" in text(tg)

    session = only_session(tg)
    rows = rows_by_slug(session, catalog)
    assert session.status == "finished"
    assert (rows["bench-press"].sets_done, rows["bench-press"].reps_done, rows["bench-press"].load_done) == (3, "10", 60.0)
    assert rows["bench-press"].rpe == 8.0
    assert (rows["barbell-back-squat"].sets_done, rows["barbell-back-squat"].load_done) == (1, 80.0)


def test_every_change_is_saved_at_once(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 1
    press(tg, "➕ Підхід")
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


# --- an existing session --------------------------------------------------------------------


def save_on_server(h, catalog, items):
    payload = [
        {"exercise": {"id": catalog[slug].id}, **values} for slug, values in items
    ]
    return h.http.request("POST", "http://localhost/api/training/sessions/complete", json={"exercises": payload}).json()


def test_existing_session_can_be_edited(tg, catalog):
    first = save_on_server(
        tg,
        catalog,
        [
            ("bench-press", {"sets": 3, "reps": 10, "load": 60, "rpe": 8}),
            ("lat-pulldown", {"sets": 3, "reps": 12, "load": 45}),
            ("plank", {"sets": 2, "duration_sec": 60}),
        ],
    )
    tg.message(TRAINING)
    assert "Всього: 3 вправи · 8 підходів" in text(tg)

    press(tg, "✏️ 1.")
    assert "Сьогодні: 3 × 10 · 60 кг · RIR 2" in text(tg)
    press(tg, "+1 повт")
    press(tg, "+2,5 кг")
    press(tg, "1")  # RIR 1
    press(tg, "➖ Підхід")
    assert "Сьогодні: 2 × 11 · 62,5 кг · RIR 1" in text(tg)

    press(tg, "← Тренування")
    press(tg, "✏️ 2.")
    press(tg, "🗑 Вправу")
    assert "Видалити «Тяга верхнього блока» (3 підходи)" in text(tg)
    press(tg, "🗑 Так, видалити")
    assert "Тяга верхнього блока" not in text(tg)
    assert "Всього: 2 вправи · 4 підходи" in text(tg)

    session = only_session(tg)
    assert session.id == first["id"]
    rows = rows_by_slug(session, catalog)
    assert set(rows) == {"bench-press", "plank"}
    bench = rows["bench-press"]
    assert (bench.sets_done, bench.reps_done, bench.load_done, bench.rpe) == (2, "11", 62.5, 9.0)
    assert (rows["plank"].sets_done, rows["plank"].duration_sec_done) == (2, 60)


def test_untouched_web_values_are_kept_exactly(tg, catalog):
    """Reps "8-12" and RPE 7.5 from the website survive edits of other exercises."""
    save_on_server(
        tg,
        catalog,
        [
            ("bench-press", {"sets": 3, "reps": "8-12", "load": 60, "rpe": 7.5}),
            ("plank", {"sets": 2, "duration_sec": 60}),
        ],
    )
    tg.message(TRAINING)
    press(tg, "✏️ 2.")
    press(tg, "➕ Підхід")

    bench = rows_by_slug(only_session(tg), catalog)["bench-press"]
    assert (bench.reps_done, bench.rpe) == ("8-12", 7.5)


def test_recent_exercise_is_one_tap_and_shows_last_time(tg, catalog):
    import datetime as dt

    from backend.app.models.training_session import SessionExercise

    past = TrainingSession(
        user_id=tg.user.id,
        status="finished",
        started_at=dt.datetime.utcnow() - dt.timedelta(days=2),
        finished_at=dt.datetime.utcnow() - dt.timedelta(days=2),
    )
    db.session.add(past)
    db.session.flush()
    db.session.add(SessionExercise(session_id=past.id, exercise_id=catalog["bench-press"].id, sets_done=3, reps_done="8", load_done=60, rpe=8))
    db.session.commit()

    tg.message(TRAINING)
    press(tg, "⭐ Жим штанги лежачи")
    assert "Минулого разу: 3 × 8 · 60 кг · RIR 2" in text(tg)
    assert button(tg, "➕ Підхід").text == "➕ Підхід · 8 · 60 кг · RIR 2"
    press(tg, "➕ Підхід")
    assert "Сьогодні: 1 × 8 · 60 кг · RIR 2" in text(tg)
    assert len(sessions(tg)) == 2  # the old one and today's


# --- search ------------------------------------------------------------------------------------


def test_typo_search(tg, catalog):
    tg.message(TRAINING)
    tg.message("підтягуваня")
    assert any(b.text == "Підтягування" for b in buttons(tg))


def test_search_without_results(tg, catalog):
    tg.message(TRAINING)
    tg.message("xyzqqq")
    assert "Нічого не знайдено" in text(tg)
    assert [b.text for b in buttons(tg)] == ["← Тренування"]


def test_more_results(tg, catalog):
    tg.message(TRAINING)
    tg.message("жим")
    before = len(buttons(tg))
    press(tg, "Ще результати")
    assert len(buttons(tg)) > before


def test_duration_exercise_uses_seconds(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "планка", "Планка")
    assert any(b.text == "+5 с" for b in buttons(tg))
    assert not any("кг" in b.text for b in buttons(tg))
    tg.message("45")
    assert "Сьогодні: 1 × 45 с" in text(tg)
    assert rows_by_slug(only_session(tg), catalog)["plank"].duration_sec_done == 45


def test_invalid_quick_input_is_explained_and_not_saved(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10 15")
    assert text(tg) == "RIR: від 0 до 9."
    tg.message("60 8,5")
    assert "цілі числа" in text(tg)
    assert sessions(tg) == []


# --- reliability -------------------------------------------------------------------------------


def test_double_tap_adds_one_set(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    data = button(tg, "➕ Підхід").callback_data
    tg.callback(data)
    tg.callback(data)  # the same screen pressed again

    assert "Екран оновлено." in toasts(tg)
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


def test_removing_the_last_set_of_the_only_exercise_deletes_the_session(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    assert len(sessions(tg)) == 1
    press(tg, "➖ Підхід")
    assert sessions(tg) == []
    press(tg, "← Тренування")
    assert "Сьогодні ще немає вправ" in text(tg)

    # and logging again creates exactly one new session
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    assert len(sessions(tg)) == 1


def test_deleting_the_last_exercise_leaves_no_empty_session(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    press(tg, "🗑 Вправу")
    press(tg, "🗑 Так, видалити")
    assert sessions(tg) == []
    assert "Сьогодні ще немає вправ" in text(tg)


def test_finishing_twice_keeps_one_session(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    press(tg, "← Тренування")
    press(tg, "✅ Завершити")
    data = press(tg, "✅ Завершити")
    tg.callback(data)  # finished already
    assert "Тренування збережено" in text(tg)
    assert only_session(tg).status == "finished"


def test_finish_without_sets_is_refused(tg, catalog):
    tg.message(TRAINING)
    tg.callback("tr:finish")
    assert "Ще немає жодного підходу." in toasts(tg)


def test_session_continues_after_finishing(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    tg.callback("tr:finyes")
    tg.message(TRAINING)
    assert "1. Жим штанги лежачи — 1 × 10 · 60 кг" in text(tg)
    press(tg, "✏️ 1.")
    press(tg, "➕ Підхід")
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


def test_cancel_leaves_the_flow_and_keeps_data(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    tg.message("/cancel")
    assert "Скасовано. Усе, що ви вже записали, збережено." in text(tg)
    tg.message("жим")
    assert "Не зрозумів" in text(tg)
    assert len(sessions(tg)) == 1


def test_close_button(tg, catalog):
    tg.message(TRAINING)
    press(tg, "❌ Скасувати")
    assert "Тренування закрито" in text(tg)


def test_menu_buttons_are_not_searched(tg, catalog):
    tg.message(TRAINING)
    tg.message(NUTRITION)
    assert "🔎" not in text(tg)
    assert "Харчування сьогодні" in text(tg)


def test_old_screen_after_a_bot_restart(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    stale = button(tg, "➕ Підхід").callback_data

    restarted = Harness()  # fresh dispatcher and empty FSM storage
    restarted.session.calls.clear()
    try:
        restarted.callback(stale)
        assert "Екран оновлено." in toasts(restarted)
        assert "1. Жим штанги лежачи — 1 × 10 · 60 кг" in text(restarted)
        press(restarted, "✏️ 1.")
        press(restarted, "➕ Підхід")
    finally:
        restarted.close()
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


def test_stale_session_id_is_not_turned_into_a_new_session(tg, catalog, monkeypatch):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    # Midnight passes: today's session is now yesterday's.
    session = only_session(tg)
    import datetime as dt

    session.started_at -= dt.timedelta(days=1)
    db.session.commit()

    press(tg, "➕ Підхід")
    assert any("уже закрите" in t for t in toasts(tg))
    assert "Сьогодні ще немає вправ" in text(tg)  # today's (empty) workout at once
    assert len(sessions(tg)) == 1
    assert only_session(tg).exercises[0].sets_done == 1


def test_network_error_keeps_the_screen_and_the_data(tg, catalog):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    tg.message("60 10")
    tg.http.down = True
    press(tg, "➕ Підхід")
    assert "Не вдалося підключитися до NosiFit." in toasts(tg)
    tg.http.down = False

    press(tg, "➕ Підхід")  # the screen is still current
    assert rows_by_slug(only_session(tg), catalog)["bench-press"].sets_done == 2


def test_server_error_is_human(tg, catalog, monkeypatch):
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")

    def broken(*args, **kwargs):
        raise NosiFitAPIError("Щось пішло не так. Спробуйте ще раз.", "internal_server_error")

    monkeypatch.setattr(NosiFitAPI, "save_session", broken)
    tg.message("60 10")
    assert text(tg) == "Не вдалося зберегти. Спробуйте ще раз."


def test_search_error_is_human(tg, catalog, monkeypatch):
    tg.message(TRAINING)
    tg.http.down = True
    tg.message("жим")
    assert text(tg) == "Не вдалося підключитися до NosiFit."


def test_expired_link_asks_to_sign_in_again(tg, catalog):
    tg.message(TRAINING)
    TelegramIdentity.query.delete()
    db.session.commit()
    tg.message("жим")
    assert "Сесія закінчилась" in text(tg)
    assert runtime._sessions[ALICE.id].expired


def test_signed_out_user_is_asked_to_sign_in(tg, catalog):
    runtime._sessions.clear()
    tg.message(TRAINING)
    assert "Спочатку увійдіть" in text(tg)


def test_flow_without_server_calls_for_drafts(tg, catalog, monkeypatch):
    """Adjusting an exercise with no sets yet saves nothing."""
    tg.message(TRAINING)
    open_new_exercise(tg, "жим штанги лежачи", "Жим штанги лежачи")
    calls = []
    original = NosiFitAPI.save_session
    monkeypatch.setattr(NosiFitAPI, "save_session", lambda self, *a: calls.append(a) or original(self, *a))
    press(tg, "+2,5 кг")
    press(tg, "+1 повт")
    assert calls == []
    assert "Підхід · 11 · 2,5 кг" in button(tg, "➕ Підхід").text
