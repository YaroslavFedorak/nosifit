from datetime import datetime, timedelta
from typing import Optional, List

from myapp.app import db
from myapp.app.models.recovery.sleep_entry import SleepEntry
from myapp.app.models.user import User
from myapp.app.services.recovery.constants import (
    BASE_SLEEP_SCORE,
    MAX_SLEEP_BONUS,
    MIN_SLEEP_SCORE,
    MAX_SLEEP_SCORE,
    SLEEP_DEBT_DAYS,
)


class SleepService:
    def get_user(self, user_id: int) -> Optional[User]:
        return db.session.get(User, user_id)

    def add_sleep(
        self, user_id: int, sleep_start: datetime, sleep_end: datetime
    ) -> SleepEntry:
        if sleep_end <= sleep_start:
            raise ValueError("sleep_end must be later than sleep_start")

        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")

        duration_minutes = int((sleep_end - sleep_start).total_seconds() // 60)

        entry = SleepEntry(
            user_id=user_id,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            duration_minutes=duration_minutes,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    def get_last_sleep(self, user_id: int) -> Optional[SleepEntry]:
        return (
            SleepEntry.query.filter_by(user_id=user_id)
            .order_by(SleepEntry.sleep_end.desc())
            .first()
        )

    def get_last_days(
        self, user_id: int, days: int = SLEEP_DEBT_DAYS
    ) -> List[SleepEntry]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            SleepEntry.query.filter(
                SleepEntry.user_id == user_id,
                SleepEntry.sleep_end >= cutoff,
            )
            .order_by(SleepEntry.sleep_end.desc())
            .all()
        )

    def calculate_sleep_score(self, duration_minutes: int) -> int:
        hours = duration_minutes / 60.0

        if hours < 0.5:
            return 20
        if 0.5 <= hours < 1.5:
            return 40
        if 1.5 <= hours < 3:
            return 55
        if 3 <= hours < 4:
            return 60
        if 4 <= hours <= 8:
            ratio = (hours - 4.0) / 4.0
            score = MIN_SLEEP_SCORE + ratio * (BASE_SLEEP_SCORE - MIN_SLEEP_SCORE)
            return int(score)
        if 8 < hours <= 9:
            return BASE_SLEEP_SCORE + MAX_SLEEP_BONUS
        if 9 < hours <= 12:
            return 80
        if 12 < hours <= 18:
            return 60
        return 40

    def calculate_sleep_debt_minutes(self, user_id: int, required_minutes: int) -> int:
        entries = self.get_last_days(user_id)
        if not entries:
            return 0

        total_deficit = sum(
            max(0, required_minutes - e.duration_minutes) for e in entries
        )
        return total_deficit // len(entries)
