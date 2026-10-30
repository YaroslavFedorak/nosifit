from backend.app.services.training.load.index import (
    compute_daily_load_index as _compute_daily_load_index,
)
from backend.app.utils import clock


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
            target_day or clock.today(),
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
            target_day or clock.today(),
        )


def compute_daily_load_index(
    user,
    sessions,
    target_day=None,
):
    return _compute_daily_load_index(
        user,
        sessions,
        target_day or clock.today(),
    )


__all__ = [
    "TrainingLoadIndexService",
    "compute_daily_load_index",
]

