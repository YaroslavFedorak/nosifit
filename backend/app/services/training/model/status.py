"""Per-muscle status: exposure, fatigue, readiness and user-facing states.

States are derived only from history, so they are deterministic. Hysteresis
is applied by replaying the last STATE_REPLAY_DAYS days, which keeps labels
from flapping without storing any state.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Mapping, Optional, Sequence

from . import parameters as P
from .context import TrainingContext
from .history import last_trained, muscle_exposure, muscle_fatigue, trend
from .readiness import (
    LEVEL_NAMES,
    hysteresis_index,
    readiness_from_fatigue,
    readiness_level_index,
    sleep_modifier,
)
from .records import SleepNight
from .stimulus import Dose

VOLUME_ZONES = ("below", "within", "above")


@dataclass(frozen=True)
class MuscleStatus:
    muscle: str
    major: bool
    exposure_recent: float  # E7 now, effective sets / week
    exposure_smoothed: float  # mean of the last 7 end-of-day E7 values (zones)
    exposure_long: float  # E28, average effective sets / week
    trend: str
    fatigue: float  # residual local fatigue, set-units (internal)
    readiness_score: float  # internal, [0, 1]
    readiness_level: str  # low | moderate | ready | recovered
    sleep_modifier: float
    lower_target: Optional[float]
    upper_target: Optional[float]
    volume_zone: Optional[str]  # below | within | above (major muscles only)
    below_target: bool  # this week
    underloaded: bool  # systematically below target
    high_volume: bool
    accumulated_fatigue: bool
    insufficient_history: bool
    days_since_trained: Optional[float]
    state: str


def weekly_targets(context: TrainingContext):
    return P.WEEKLY_SET_TARGETS[context.goal][context.experience]


def _end_of_day(day: date, now: datetime) -> datetime:
    return min(datetime.combine(day, time.max), now)


def _all_muscles(doses: Sequence[Dose], extra: Sequence[str]) -> List[str]:
    names = set(extra)
    for dose in doses:
        names.update(muscle for muscle, _ in dose.muscle_stimulus)
    return sorted(names)


def compute_statuses(
    doses: Sequence[Dose],
    sleep: Sequence[SleepNight],
    context: TrainingContext,
    now: datetime,
    history_start: Optional[datetime] = None,
) -> Dict[str, MuscleStatus]:
    lower, upper = weekly_targets(context)
    muscles = _all_muscles(doses, P.MAJOR_MUSCLES)
    today = now.date()

    replay_days = [today - timedelta(days=offset) for offset in range(P.STATE_REPLAY_DAYS - 1, -1, -1)]
    smoothing = P.VOLUME_ZONE_SMOOTHING_DAYS
    readiness_by_day: Dict[date, Dict[str, float]] = {}
    exposure_by_day: Dict[date, Dict[str, float]] = {}
    for offset in range(P.STATE_REPLAY_DAYS + smoothing - 2, -1, -1):
        day = today - timedelta(days=offset)
        exposure_by_day[day] = muscle_exposure(doses, _end_of_day(day, now), P.EXPOSURE_RECENT_TAU_DAYS)
    for day in replay_days:
        moment = _end_of_day(day, now)
        modifier = sleep_modifier(sleep, day)
        fatigue = muscle_fatigue(doses, moment)
        readiness_by_day[day] = {
            muscle: readiness_from_fatigue(fatigue.get(muscle, 0.0)) * modifier
            for muscle in muscles
        }

    def smoothed(muscle: str, day: date) -> float:
        values = [
            exposure_by_day[day - timedelta(days=k)].get(muscle, 0.0) for k in range(smoothing)
        ]
        return sum(values) / len(values)

    fatigue_now = muscle_fatigue(doses, now)
    e7_now = muscle_exposure(doses, now, P.EXPOSURE_RECENT_TAU_DAYS)
    e28_now = muscle_exposure(doses, now, P.EXPOSURE_LONG_TAU_DAYS)
    modifier_now = sleep_modifier(sleep, today)
    trained = last_trained(doses, now)

    first_dose = min((dose.performed_at for dose in doses), default=None)
    start = history_start if history_start is not None else first_dose
    insufficient = start is None or (now - start).days < P.MIN_HISTORY_DAYS_FOR_UNDERLOAD

    window, needed = P.ACCUMULATED_FATIGUE_DAYS[1], P.ACCUMULATED_FATIGUE_DAYS[0]
    statuses: Dict[str, MuscleStatus] = {}

    for muscle in muscles:
        major = muscle in P.MAJOR_MUSCLES

        level_index: Optional[int] = None
        zone_index: Optional[int] = None
        for day in replay_days:
            level_index = readiness_level_index(readiness_by_day[day][muscle], level_index)
            if major:
                zone_index = hysteresis_index(
                    smoothed(muscle, day),
                    (0.0, lower, upper),
                    zone_index,
                    P.VOLUME_HYSTERESIS_SETS,
                )

        # The last replayed day is today evaluated at ``now``.
        readiness_score = readiness_by_day[today][muscle]

        fatigued_days = sum(
            1
            for day in replay_days[-window:]
            if readiness_by_day[day][muscle] < P.ACCUMULATED_FATIGUE_THRESHOLD
        )
        accumulated = fatigued_days >= needed

        e7 = e7_now.get(muscle, 0.0)
        e28 = e28_now.get(muscle, 0.0)
        zone = VOLUME_ZONES[zone_index] if major and zone_index is not None else None
        below = zone == "below"
        underloaded = bool(major and below and e28 < lower and not insufficient)
        e7_smoothed = smoothed(muscle, today)

        last = trained.get(muscle)
        days_since = None if last is None else (now - last).total_seconds() / 86400.0
        level = LEVEL_NAMES[level_index]

        statuses[muscle] = MuscleStatus(
            muscle=muscle,
            major=major,
            exposure_recent=e7,
            exposure_smoothed=e7_smoothed,
            exposure_long=e28,
            trend=trend(e7, e28),
            fatigue=fatigue_now.get(muscle, 0.0),
            readiness_score=readiness_score,
            readiness_level=level,
            sleep_modifier=modifier_now,
            lower_target=float(lower) if major else None,
            upper_target=float(upper) if major else None,
            volume_zone=zone,
            below_target=below,
            underloaded=underloaded,
            high_volume=zone == "above",
            accumulated_fatigue=accumulated,
            insufficient_history=insufficient,
            days_since_trained=days_since,
            state=_state(level, accumulated, underloaded, zone),
        )

    return statuses


def _state(level: str, accumulated: bool, underloaded: bool, zone: Optional[str]) -> str:
    if accumulated:
        return "accumulated_fatigue"
    if level == "low":
        return "high_fatigue"
    if underloaded:
        return "underloaded"
    if level == "recovered" and zone != "above":
        return "recovery_available"
    return "appropriate"


def statuses_by_state(statuses: Mapping[str, MuscleStatus], *states: str) -> List[str]:
    return sorted(m for m, s in statuses.items() if s.state in states)
