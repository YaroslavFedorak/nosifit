from datetime import date, timedelta

from backend.app.models.nutrition.meal import Meal
from backend.app.models.recovery.daily_recovery_snapshot import (
    DailyRecoverySnapshot,
)
from backend.app.models.training_session import TrainingSession
from backend.app.services.dashboard.score import calculate_daily_score
from backend.app.dashboard.training.metrics import (
    calculate_training_score,
)
from backend.app.services.nutrition.quality_service import (
    calculate_quality,
)


def _day_bounds(target_date):
    from datetime import datetime, time

    return (
        datetime.combine(target_date, time.min),
        datetime.combine(target_date, time.max),
    )


def _get_training_session(user_id, target_date):
    start_dt, end_dt = _day_bounds(target_date)

    return (
        TrainingSession.query.filter(
            TrainingSession.user_id == user_id,
            TrainingSession.started_at >= start_dt,
            TrainingSession.started_at <= end_dt,
            TrainingSession.status == "finished",
        )
        .order_by(TrainingSession.started_at.desc())
        .first()
    )


def _get_training_data(user_id, target_date):
    session = _get_training_session(
        user_id,
        target_date,
    )

    if not session:
        return {
            "score": None,
            "completed": False,
            "duration": 0,
            "exercise_count": 0,
        }

    return {
        "score": calculate_training_score(session),
        "completed": True,
        "duration": _get_duration(session),
        "exercise_count": len(session.exercises),
    }


def _get_duration(session):
    if not session.started_at:
        return 0

    end = session.finished_at

    if not end:
        return 0

    seconds = (end - session.started_at).total_seconds()

    if seconds <= 0:
        return 0

    return int(round(seconds / 60))


def _get_nutrition_data(user_id, target_date):
    meals = (
        Meal.query.filter(
            Meal.user_id == user_id,
            Meal.date == target_date,
        )
        .order_by(
            Meal.time.asc().nullsfirst(),
            Meal.id.asc(),
        )
        .all()
    )

    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    ration_items = []

    for meal in meals:
        total_calories += meal.total_calories or 0
        total_protein += meal.total_protein or 0
        total_fat += meal.total_fat or 0
        total_carbs += meal.total_carbs or 0

        for item in meal.items:
            ration_items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "calories": item.calories or 0,
                    "protein": item.protein or 0,
                    "fat": item.fat or 0,
                    "carbs": item.carbs or 0,
                    "fiber": item.fiber or 0,
                }
            )

    if not meals:
        score = None
    else:
        quality = calculate_quality(ration_items)
        score = quality.get("score")

    return {
        "score": score,
        "calories": total_calories,
        "protein": total_protein,
        "water": 0,
    }


def _get_recovery_data(user_id, target_date):
    snapshot = DailyRecoverySnapshot.query.filter_by(
        user_id=user_id,
        date=target_date,
    ).first()

    if not snapshot:
        return {
            "score": None,
            "sleep_hours": 0,
            "habits_completed": 0,
            "habits_total": 0,
        }

    sleep_hours = 0

    if snapshot.sleep_duration_minutes:
        sleep_hours = round(
            snapshot.sleep_duration_minutes / 60,
            1,
        )

    return {
        "score": snapshot.recovery_score,
        "sleep_hours": sleep_hours,
        "habits_completed": 0,
        "habits_total": 0,
    }


def _build_day(user_id, target_date):
    training = _get_training_data(
        user_id,
        target_date,
    )

    nutrition = _get_nutrition_data(
        user_id,
        target_date,
    )

    recovery = _get_recovery_data(
        user_id,
        target_date,
    )

    daily_score = calculate_daily_score(
        training.get("score"),
        nutrition.get("score"),
        recovery.get("score"),
    )

    return {
        "date": target_date.isoformat(),
        "daily_score": daily_score,
        "training": training,
        "nutrition": nutrition,
        "recovery": recovery,
    }


def get_today_overview(user_id):
    return _build_day(
        user_id,
        date.today(),
    )


def get_heatmap(user_id):
    today = date.today()
    start_date = today - timedelta(days=364)

    days = []

    current_date = start_date

    while current_date <= today:
        data = _build_day(
            user_id,
            current_date,
        )

        has_data = (
            data["training"]["score"] is not None
            or data["nutrition"]["score"] is not None
            or data["recovery"]["score"] is not None
        )

        if has_data:
            daily_score = data["daily_score"]

            if daily_score <= 0:
                level = 0
            elif daily_score <= 20:
                level = 1
            elif daily_score <= 40:
                level = 2
            elif daily_score <= 60:
                level = 3
            elif daily_score <= 80:
                level = 4
            elif daily_score <= 90:
                level = 5
            else:
                level = 6

            days.append(
                {
                    **data,
                    "level": level,
                }
            )

        current_date += timedelta(days=1)

    return {
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
    }

