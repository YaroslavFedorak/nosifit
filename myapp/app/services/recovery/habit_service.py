from datetime import date
from myapp.app import db
from myapp.app.models.recovery.habit import RecoveryHabit
from myapp.app.models.recovery.user_habit import UserRecoveryHabit
from myapp.app.models.recovery.habit_log import RecoveryHabitLog


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
        habit_ids = [h.habit_id for h in user_habits]
        if not habit_ids:
            return []
        habits = RecoveryHabit.query.filter(RecoveryHabit.id.in_(habit_ids)).all()
        return habits

    def add_user_habit(self, user_id, habit_id):
        existing = UserRecoveryHabit.query.filter_by(
            user_id=user_id, habit_id=habit_id
        ).first()

        if existing:
            existing.is_active = True
            db.session.commit()
            return existing, False

        habit = UserRecoveryHabit(user_id=user_id, habit_id=habit_id)
        db.session.add(habit)
        db.session.commit()
        return habit, True

    def remove_user_habit(self, user_habit_id):
        habit = UserRecoveryHabit.query.get(user_habit_id)
        if not habit:
            return None
        habit.is_active = False
        db.session.commit()
        return habit

    def log_habit(self, user_habit_id):
        habit = UserRecoveryHabit.query.get(user_habit_id)
        if not habit:
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
                date=today,
                completed=True,
                completed_at=db.func.now(),
            )
            db.session.add(log)

        db.session.commit()
        return log

    def get_today_logs(self, user_id):
        habits = self.get_user_habits(user_id)
        ids = [h.id for h in habits]

        if not ids:
            return []

        return RecoveryHabitLog.query.filter(
            RecoveryHabitLog.user_habit_id.in_(ids),
            RecoveryHabitLog.date == date.today(),
        ).all()
