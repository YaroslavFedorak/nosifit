from datetime import date

from backend.app.extensions import db
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.recovery.habit_log import RecoveryHabitLog


class HabitService:
    def get_all_habits(self):
        return (
            RecoveryHabit.query.filter_by(is_active=True)
            .order_by(RecoveryHabit.sort_order)
            .all()
        )

    def get_user_habits(self, user_id):
        return UserRecoveryHabit.query.filter_by(user_id=user_id, is_active=True).all()

    def get_user_habits_full(self, user_id):
        user_habits = self.get_user_habits(user_id)

        if not user_habits:
            return []

        habit_ids = [user_habit.habit_id for user_habit in user_habits]

        habits = RecoveryHabit.query.filter(RecoveryHabit.id.in_(habit_ids)).all()

        habit_map = {habit.id: habit for habit in habits}

        return [
            {
                "user_habit_id": user_habit.id,
                "id": habit.id,
                "name": habit.name,
                "category": habit.category,
                "points": habit.points,
                "icon": habit.icon,
                "completed": False,
            }
            for user_habit in user_habits
            if (habit := habit_map.get(user_habit.habit_id))
        ]

    def get_user_habits_with_status(self, user_id, target_date: date = None):
        target_date = target_date or date.today()

        user_habits = self.get_user_habits(user_id)

        if not user_habits:
            return []

        user_habit_ids = [user_habit.id for user_habit in user_habits]

        logs = RecoveryHabitLog.query.filter(
            RecoveryHabitLog.user_habit_id.in_(user_habit_ids),
            RecoveryHabitLog.date == target_date,
            RecoveryHabitLog.completed.is_(True),
        ).all()

        completed_ids = {log.user_habit_id for log in logs}

        habit_ids = [user_habit.habit_id for user_habit in user_habits]

        habits = RecoveryHabit.query.filter(RecoveryHabit.id.in_(habit_ids)).all()

        habit_map = {habit.id: habit for habit in habits}

        result = []

        for user_habit in user_habits:
            habit = habit_map.get(user_habit.habit_id)

            if not habit:
                continue

            result.append(
                {
                    "user_habit_id": user_habit.id,
                    "id": habit.id,
                    "name": habit.name,
                    "category": habit.category,
                    "points": habit.points,
                    "icon": habit.icon,
                    "completed": (user_habit.id in completed_ids),
                }
            )

        return result

    def ensure_user_has_habit(self, user_id, habit_id):
        existing = UserRecoveryHabit.query.filter_by(
            user_id=user_id, habit_id=habit_id
        ).first()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.session.commit()

            return existing

        habit = UserRecoveryHabit(user_id=user_id, habit_id=habit_id)

        db.session.add(habit)
        db.session.commit()

        return habit

    def add_user_habit(self, user_id, habit_id):
        existing = UserRecoveryHabit.query.filter_by(
            user_id=user_id, habit_id=habit_id
        ).first()

        if existing:
            was_inactive = not existing.is_active

            existing.is_active = True

            db.session.commit()

            return existing, was_inactive

        habit = UserRecoveryHabit(user_id=user_id, habit_id=habit_id)

        db.session.add(habit)
        db.session.commit()

        return habit, True

    def remove_user_habit(self, user_habit_id):
        habit = db.session.get(UserRecoveryHabit, user_habit_id)

        if not habit:
            return None

        habit.is_active = False

        db.session.commit()

        return habit

    def log_habit(self, user_habit_id):
        habit = db.session.get(UserRecoveryHabit, user_habit_id)

        if not habit or not habit.is_active:
            return None

        today = date.today()

        log = RecoveryHabitLog.query.filter_by(
            user_habit_id=user_habit_id, date=today
        ).first()

        if log:
            log.completed = True
            log.completed_at = db.func.now()
        else:
            log = RecoveryHabitLog(
                user_habit_id=user_habit_id,
                user_id=habit.user_id,
                date=today,
                completed=True,
                completed_at=db.func.now(),
            )

            db.session.add(log)

        db.session.commit()

        return log

    def unlog_habit(self, user_habit_id):
        habit = db.session.get(UserRecoveryHabit, user_habit_id)

        if not habit:
            return None

        today = date.today()

        log = RecoveryHabitLog.query.filter_by(
            user_habit_id=user_habit_id, date=today
        ).first()

        if not log:
            return False

        db.session.delete(log)
        db.session.commit()

        return True

    def get_today_logs(self, user_id, target_date: date = None):
        target_date = target_date or date.today()

        habits = self.get_user_habits(user_id)

        ids = [habit.id for habit in habits]

        if not ids:
            return []

        return RecoveryHabitLog.query.filter(
            RecoveryHabitLog.user_habit_id.in_(ids),
            RecoveryHabitLog.date == target_date,
        ).all()

