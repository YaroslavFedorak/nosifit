"""Orchestration of the training model.

    entries -> doses (stimulus | fatigue) -> exposure | readiness -> status
            -> Stage 1 muscle plan -> Stage 2 exercises -> prescription

and, as a separate tree, doses -> session stress proxy -> dashboard/heatmap.

``analyse`` is pure; ``TrainingModelService`` adds the batched DB loading.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable, Dict, List, Mapping, Optional, Sequence

from . import parameters as P
from . import repository
from .context import TrainingContext
from .history import build_doses, last_done
from .priority import MusclePlan, plan_muscles
from .progression import analyse_progression
from .readiness import readiness_from_fatigue
from .records import ExerciseInfo, LoggedEntry, SleepNight
from .selection import ExercisePrescription, select_exercises
from .session_stress import daily_stress, day_levels, summarize
from .status import MuscleStatus, compute_statuses
from .stimulus import Dose
from .weekly_sets import week_start, weekly_muscle_sets


@dataclass
class TrainingAnalysis:
    now: datetime
    context: TrainingContext
    catalog: Mapping[str, ExerciseInfo]
    entries: List[LoggedEntry]
    doses: List[Dose]
    statuses: Dict[str, MuscleStatus]
    plans: List[MusclePlan]
    exercises: List[ExercisePrescription]
    progression: Dict


def analyse(
    context: TrainingContext,
    catalog: Mapping[str, ExerciseInfo],
    entries: Sequence[LoggedEntry],
    sleep: Sequence[SleepNight],
    now: datetime,
) -> TrainingAnalysis:
    entries = [e for e in entries if e.performed_at <= now]
    doses = build_doses(entries, catalog, context.body_weight_kg)
    statuses = compute_statuses(doses, sleep, context, now)
    plans = plan_muscles(statuses, context)
    exercises = select_exercises(
        plans,
        statuses,
        list(catalog.values()),
        context,
        last_done(doses, now),
        now,
    )
    return TrainingAnalysis(
        now=now,
        context=context,
        catalog=catalog,
        entries=list(entries),
        doses=doses,
        statuses=statuses,
        plans=plans,
        exercises=exercises,
        progression=analyse_progression(entries, catalog, now),
    )


def moment_for(target_day: Optional[date], now: Optional[datetime] = None) -> datetime:
    """Evaluation time: now for today (or no day), end of day for past days."""
    current = now or datetime.utcnow()
    if target_day is None or target_day >= current.date():
        return current
    return datetime.combine(target_day, time.max)


class TrainingModelService:
    @staticmethod
    def analyse_user(
        user,
        target_day: Optional[date] = None,
        sessions: Optional[Sequence] = None,
        now: Optional[datetime] = None,
    ) -> TrainingAnalysis:
        moment = moment_for(target_day, now)
        since = moment - timedelta(days=P.HISTORY_DAYS)
        catalog = repository.load_catalog()
        if sessions is None:
            sessions = repository.load_sessions(user.id, since, moment)
        else:
            sessions = [
                s for s in sessions
                if repository.session_time(s) is not None
                and since <= repository.session_time(s) <= moment
            ]
        entries = repository.entries_from_sessions(sessions, catalog)
        sleep_since = moment.date() - timedelta(days=P.SLEEP_LOOKBACK_NIGHTS + P.STATE_REPLAY_DAYS)
        sleep = repository.load_sleep(user.id, sleep_since) if getattr(user, "id", None) else []
        context = repository.load_context(user)
        return analyse(context, catalog, entries, sleep, moment)

    @staticmethod
    def session_summary(session) -> Dict:
        """hard_sets, stress proxy, tonnage and muscle_sets of one session.

        Earlier sessions are loaded only to know which exercises are new
        (novelty affects the fatigue-based stress proxy)."""
        moment = repository.session_time(session)
        if moment is None:
            return summarize([])
        catalog = repository.load_catalog()
        history = repository.load_sessions(
            session.user_id, moment - timedelta(days=P.NOVELTY_UNFAMILIAR_DAYS + 1), moment
        )
        if all(s.id != session.id for s in history):
            history = list(history) + [session]
        context = repository.load_context(session.user) if getattr(session, "user", None) else TrainingContext()
        doses = build_doses(repository.entries_from_sessions(history, catalog), catalog, context.body_weight_kg)
        return summarize(d for d in doses if d.session_id == session.id)

    @staticmethod
    def stress_days(
        user_id: int,
        days: Sequence[date],
        day_of: Callable[[datetime], date],
        since: datetime,
        until: datetime,
    ) -> Dict[date, Dict]:
        """Heatmap tree: per-day stress proxy and level vs the typical session."""
        if not days:
            return {}
        catalog = repository.load_catalog()
        baseline_since = since - timedelta(days=P.STRESS_BASELINE_DAYS + P.NOVELTY_UNFAMILIAR_DAYS)
        sessions = repository.load_sessions(user_id, baseline_since, until)
        doses = build_doses(repository.entries_from_sessions(sessions, catalog), catalog)
        per_day = daily_stress(doses, day_of)
        levels = day_levels(per_day, days)
        hard: Dict[date, float] = {}
        for dose in doses:
            day = day_of(dose.performed_at)
            hard[day] = hard.get(day, 0.0) + dose.stimulus_sets
        for day in days:
            levels[day]["hard_sets"] = round(hard.get(day, 0.0), 1)
        return levels

    @staticmethod
    def day_stress(user_id: int, target_day: date) -> Dict:
        """Stress proxy of one (UTC) day and the user's typical session."""
        start = datetime.combine(target_day, time.min)
        result = TrainingModelService.stress_days(
            user_id,
            [target_day],
            lambda moment: moment.date(),
            start,
            datetime.combine(target_day, time.max),
        )
        return result[target_day]

    @staticmethod
    def weekly_sets(
        user,
        today: date,
        day_of: Callable[[datetime], date],
        until: datetime,
    ) -> Dict:
        """Effective sets per major muscle from Monday through ``today``.

        Sessions are placed on days like the heatmap does: by
        ``finished_at or started_at`` mapped through ``day_of``. The query
        starts a day early so a session started late on Sunday and finished
        on Monday is still found."""
        start = week_start(today)
        since = datetime.combine(start - timedelta(days=1), time.min)
        sessions = repository.load_sessions(user.id, since, until)
        loads = [
            session.muscle_loads
            for session in sessions
            if repository.session_time(session) is not None
            and start <= day_of(repository.session_time(session)) <= today
        ]
        result = weekly_muscle_sets(loads, repository.load_context(user))
        result["week_start"] = start.isoformat()
        result["week_end"] = today.isoformat()
        return result

    @staticmethod
    def training_readiness_score(user, target_day: Optional[date] = None) -> int:
        """0-100 readiness of recently trained muscles, sleep excluded (the
        recovery snapshot weighs sleep separately). 100 without recent training."""
        analysis = TrainingModelService.analyse_user(user, target_day)
        values = [
            readiness_from_fatigue(status.fatigue)
            for status in analysis.statuses.values()
            if status.days_since_trained is not None
            and status.days_since_trained <= P.TRAINING_READINESS_LOOKBACK_DAYS
        ]
        if not values:
            return 100
        return int(round(100 * sum(values) / len(values)))
