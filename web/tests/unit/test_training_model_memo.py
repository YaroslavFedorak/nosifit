"""One analysis of the training history per request (request_memo.py)."""

import datetime as dt

from sqlalchemy import event

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.training.model import TrainingModelService
from backend.app.services.training.model import request_memo
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise


def _count_queries(fn):
    statements = []

    def before(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", before)
    try:
        result = fn()
    finally:
        event.remove(db.engine, "before_cursor_execute", before)
    return result, len(statements)


def _workout(user, day):
    exercise = Exercise.query.order_by(Exercise.id).first()
    started = dt.datetime.combine(day, dt.time(8))
    session = TrainingSession(user_id=user.id, started_at=started, finished_at=started + dt.timedelta(hours=1), status="finished")
    db.session.add(session)
    db.session.flush()
    db.session.add(SessionExercise(session_id=session.id, exercise_id=exercise.id, sets_done=4, reps_done=8, load_done=60))
    db.session.commit()


def _catalog():
    for item in load_exercise_catalog()[:20]:
        db.session.add(Exercise(**item))
    db.session.commit()


def test_a_read_analyses_once(app, user):
    _catalog()
    with app.test_request_context("/api/dashboard/recommendation", method="GET"):
        first, first_queries = _count_queries(lambda: TrainingModelService.analyse_user(user))
        again, again_queries = _count_queries(lambda: TrainingModelService.analyse_user(user, dt.date.today()))
    assert again is first
    assert first_queries > 0 and again_queries == 0


def test_past_days_are_kept_apart_from_today(app, user):
    _catalog()
    yesterday = dt.date.today() - dt.timedelta(days=1)
    with app.test_request_context("/", method="GET"):
        today = TrainingModelService.analyse_user(user)
        past = TrainingModelService.analyse_user(user, yesterday)
        assert past is not today
        assert TrainingModelService.analyse_user(user, yesterday) is past


def test_each_request_starts_empty(app, user):
    _catalog()
    with app.test_request_context("/", method="GET"):
        first = TrainingModelService.analyse_user(user)
    with app.test_request_context("/", method="GET"):
        assert TrainingModelService.analyse_user(user) is not first


def test_writes_are_never_served_from_the_memo(app, user):
    _catalog()
    with app.test_request_context("/api/training/sessions/complete", method="POST"):
        first = TrainingModelService.analyse_user(user)
        assert TrainingModelService.analyse_user(user) is not first


def test_a_write_during_a_read_clears_the_memo(app, user):
    _catalog()
    with app.test_request_context("/", method="GET"):
        before = TrainingModelService.analyse_user(user)
        assert before.entries == []
        _workout(user, dt.date.today())
        after = TrainingModelService.analyse_user(user)
        assert after is not before
        assert len(after.entries) == 1


def test_day_stress_is_shared_but_handed_out_as_copies(app, user):
    _catalog()
    _workout(user, dt.date.today())
    with app.test_request_context("/", method="GET"):
        first, first_queries = _count_queries(lambda: TrainingModelService.day_stress(user.id, dt.date.today()))
        first["changed_by_a_caller"] = True
        second, second_queries = _count_queries(lambda: TrainingModelService.day_stress(user.id, dt.date.today()))
    assert first_queries > 0 and second_queries == 0
    assert "changed_by_a_caller" not in second


def test_a_commit_without_the_orm_clears_the_memo_too(app, user):
    _catalog()
    with app.test_request_context("/", method="GET"):
        before = TrainingModelService.analyse_user(user)
        db.session.execute(db.text("UPDATE users SET weight = 81 WHERE id = :id"), {"id": user.id})
        db.session.commit()
        assert TrainingModelService.analyse_user(user) is not before


def test_forget_is_harmless_without_a_memo(app):
    with app.test_request_context("/", method="GET"):
        request_memo.forget()
        request_memo.forget()
