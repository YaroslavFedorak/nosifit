from datetime import datetime

from sqlalchemy.orm import selectinload

from backend.app.extensions import db
from backend.app.models.training_session import (
    SessionExercise,
    TrainingSession,
)
from backend.app.services.training.load import calculate_session_load
from backend.app.services.training.model import TrainingModelService
from backend.app.training.exercises.prescription import session_update_fields
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.performance_state import PerformanceState
from backend.app.utils import clock


class TrainingSessionService:

    @staticmethod
    def _new_session(user, fatigue_before=None):
        session = TrainingSession(
            user_id=user.id,
            fatigue_before=fatigue_before,
            status="active",
            started_at=datetime.utcnow(),
        )

        db.session.add(session)
        db.session.flush()
        return session

    @staticmethod
    def start_session(user, fatigue_before=None):
        session = TrainingSessionService._new_session(user, fatigue_before)
        db.session.commit()
        return session

    @staticmethod
    def _exercise_row(session, exercise_id):
        row = SessionExercise.query.filter_by(
            session_id=session.id,
            exercise_id=exercise_id,
        ).first()

        if row is None:
            row = SessionExercise(
                session_id=session.id,
                exercise_id=exercise_id,
                sets_planned=0,
                sets_done=0,
            )
            db.session.add(row)
            db.session.flush()
        return row

    @staticmethod
    def add_exercise(session, exercise_id):
        session_exercise = TrainingSessionService._exercise_row(session, exercise_id)
        db.session.commit()
        return session_exercise

    @staticmethod
    def _apply_exercise(session, exercise_id, data):
        session_exercise = TrainingSessionService._exercise_row(session, exercise_id)
        exercise = db.session.get(Exercise, exercise_id)

        for field, value in session_update_fields(exercise, data).items():
            setattr(session_exercise, field, value)

        return session_exercise

    @staticmethod
    def update_exercise(session, exercise_id, data):
        session_exercise = TrainingSessionService._apply_exercise(session, exercise_id, data)
        db.session.commit()
        return session_exercise

    @staticmethod
    def _add_exercises(session, exercises):
        """Rows for ``[(exercise_id, data), ...]`` of a session that has none; no commit."""
        if not exercises:
            return
        catalog = {
            exercise.id: exercise
            for exercise in Exercise.query.filter(
                Exercise.id.in_([exercise_id for exercise_id, _ in exercises])
            )
        }
        db.session.add_all(
            SessionExercise(
                session_id=session.id,
                exercise_id=exercise_id,
                sets_planned=0,
                **{"sets_done": 0, **session_update_fields(catalog.get(exercise_id), data)},
            )
            for exercise_id, data in exercises
        )

    @staticmethod
    def _compute_session_load(session, user):
        """Store the session's figures; returns its summary for the caller."""
        # internal_load: legacy multiplier-based number, still read by the
        # dashboard session score; removed once that consumer moves.
        session.internal_load = calculate_session_load(session, user)
        # The muscle_loads column now stores effective sets per muscle (v2
        # model). It used to hold exercise ids by mistake.
        summary = TrainingModelService.session_summary(session)
        session.muscle_loads = summary["muscle_sets"]
        return summary

    @staticmethod
    def _close(session, finished_at=None):
        """Mark the session finished and store its figures; no commit."""
        session.status = "finished"
        session.finished_at = finished_at or datetime.utcnow()

        # Rows added through _apply_exercise are not in the loaded relationship.
        db.session.flush()
        db.session.expire(session, ["exercises"])

        rpes = [ex.rpe for ex in session.exercises if ex.rpe is not None]
        session.rpe_avg = sum(rpes) / len(rpes) if rpes else None

        return TrainingSessionService._compute_session_load(session, session.user)

    @staticmethod
    def _latest_performance(user_id):
        return (
            PerformanceState.query.filter_by(user_id=user_id)
            .order_by(PerformanceState.created_at.desc())
            .first()
        )

    @staticmethod
    def _add_to_training_load(session):
        """The legacy cumulative PerformanceState.training_load: the sum over sessions."""
        user = session.user
        total_load = session.internal_load or 0
        performance = TrainingSessionService._latest_performance(user.id)

        if not performance:
            performance = PerformanceState(
                user_id=user.id,
                training_load=total_load,
                weight=user.weight,
            )
            db.session.add(performance)
        else:
            performance.training_load = (performance.training_load or 0) + total_load

    @staticmethod
    def _replace_exercises(session, exercises, fatigue_after=None):
        """The session's exercises become ``exercises``; returns its summary.

        The workout page sends the whole current workout on every save, so a
        repeated save must update the session instead of creating another
        one. The legacy cumulative PerformanceState.training_load only gets
        the difference, so it still equals the sum over sessions.
        """
        previous_load = session.internal_load or 0
        session.exercises.clear()
        db.session.flush()

        TrainingSessionService._add_exercises(session, exercises)

        if fatigue_after is not None:
            session.fatigue_after = fatigue_after

        summary = TrainingSessionService._close(session)

        performance = TrainingSessionService._latest_performance(session.user_id)
        if performance is not None:
            performance.training_load = (performance.training_load or 0) + (
                (session.internal_load or 0) - previous_load
            )

        return summary

    @staticmethod
    def save_workout(user, exercises, session=None, fatigue_before=None, fatigue_after=None):
        """Store a logged workout in one transaction: all of it or nothing.

        ``session`` is today's session to save over. Without it a new finished
        session is created, and one left in progress is finished first.
        Returns ``(session, summary)``.
        """
        if session is not None:
            summary = TrainingSessionService._replace_exercises(session, exercises, fatigue_after)
        else:
            existing = TrainingSessionService.active_session(user.id)
            if existing:
                existing.fatigue_after = fatigue_after
                TrainingSessionService._close(existing)
                TrainingSessionService._add_to_training_load(existing)

            session = TrainingSessionService._new_session(user, fatigue_before)
            session.fatigue_after = fatigue_after
            TrainingSessionService._add_exercises(session, exercises)
            summary = TrainingSessionService._close(session)
            TrainingSessionService._add_to_training_load(session)

        db.session.commit()
        return session, summary

    @staticmethod
    def delete_session(session):
        """Remove a session whose last exercise was deleted.

        Clearing it first takes its share out of the legacy cumulative
        PerformanceState.training_load.
        """
        TrainingSessionService._replace_exercises(session, [])
        db.session.delete(session)
        db.session.commit()

    @staticmethod
    def last_performed(user_id, exercise_ids=None, limit=8, exclude_session_id=None):
        """Newest logged row per exercise, most recently done first.

        Rows of ``exclude_session_id`` (usually today's session) are skipped
        so they show what was done last time, not what is being logged now.
        """
        query = (
            db.session.query(SessionExercise, TrainingSession.started_at)
            .join(TrainingSession, SessionExercise.session_id == TrainingSession.id)
            .filter(TrainingSession.user_id == user_id)
        )
        if exclude_session_id is not None:
            query = query.filter(TrainingSession.id != exclude_session_id)
        if exercise_ids is not None:
            if not exercise_ids:
                return []
            query = query.filter(SessionExercise.exercise_id.in_(list(exercise_ids)))
        rows = query.order_by(
            TrainingSession.started_at.desc(), SessionExercise.id.desc()
        ).limit(500)

        seen = {}
        for row, _ in rows:
            if row.exercise_id not in seen:
                seen[row.exercise_id] = row
                if len(seen) >= limit:
                    break
        return list(seen.values())

    @staticmethod
    def finish_session(session, fatigue_after=None, finished_at=None):
        session.fatigue_after = fatigue_after
        TrainingSessionService._close(session, finished_at)
        TrainingSessionService._add_to_training_load(session)
        db.session.commit()
        return session

    @staticmethod
    def sessions_started_on(user_id, day):
        """The user's sessions started on the calendar day ``day``, oldest first."""
        start, end = clock.day_bounds_utc(day)
        return (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start,
                TrainingSession.started_at <= end,
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

    @staticmethod
    def active_session(user_id):
        """The user's newest session still in progress, if any."""
        return (
            TrainingSession.query.filter_by(user_id=user_id, status="active")
            .order_by(TrainingSession.started_at.desc())
            .first()
        )

    @staticmethod
    def session_for_user(session_id, user_id):
        return TrainingSession.query.filter_by(id=session_id, user_id=user_id).first()

    @staticmethod
    def active_session_for_user(session_id, user_id):
        return TrainingSession.query.filter_by(
            id=session_id, user_id=user_id, status="active"
        ).first()

    @staticmethod
    def latest_started_between(user_id, start, end):
        """Newest session started in [start, end) (naive UTC), if any."""
        return (
            TrainingSession.query.filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start,
                TrainingSession.started_at < end,
            )
            .order_by(TrainingSession.started_at.desc(), TrainingSession.id.desc())
            .first()
        )

    @staticmethod
    def sessions_started_within(user_id, start, end):
        """Sessions started in [start, end] (naive UTC), oldest first."""
        return (
            TrainingSession.query.options(selectinload(TrainingSession.exercises))
            .filter(
                TrainingSession.user_id == user_id,
                TrainingSession.started_at >= start,
                TrainingSession.started_at <= end,
            )
            .order_by(TrainingSession.started_at.asc(), TrainingSession.id.asc())
        )
