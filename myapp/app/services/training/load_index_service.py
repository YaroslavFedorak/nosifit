from datetime import date

from myapp.app.services.training.load.index import (
    compute_daily_load_index as _compute_daily_load_index,
)


class TrainingLoadIndexService:
    @staticmethod
    def compute(
        user,
        sessions,
        target_day=None,
    ):
        return _compute_daily_load_index(
            user,
            sessions,
            target_day or date.today(),
        )

    @staticmethod
    def compute_daily_load_index(
        user,
        sessions,
        target_day=None,
    ):
        return _compute_daily_load_index(
            user,
            sessions,
            target_day or date.today(),
        )


def compute_daily_load_index(
    user,
    sessions,
    target_day=None,
):
    return _compute_daily_load_index(
        user,
        sessions,
        target_day or date.today(),
    )


__all__ = [
    "TrainingLoadIndexService",
    "compute_daily_load_index",
]
