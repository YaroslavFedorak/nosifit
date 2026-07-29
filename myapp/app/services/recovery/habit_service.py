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

    def get_user_habits_with_status(self, user_id):
        user_habits = self.get_user_habits(user_id)
        if not user_habits:
            return []

        user_habit_ids = [h.id for h in user_habits]
        logs = RecoveryHabitLog.query.filter(
            RecoveryHabitLog.user_habit_id.in_(user_habit_ids),
            RecoveryHabitLog.date == date.today(),
        ).all()
        completed_ids = {log.user_habit_id for log in logs if log.completed}

        habit_ids = [h.habit_id for h in user_habits]
        habits = RecoveryHabit.query.filter(RecoveryHabit.id.in_(habit_ids)).all()
        habit_by_id = {h.id: h for h in habits}

        result = []
        for uh in user_habits:
            habit = habit_by_id.get(uh.habit_id)
            if habit:
                result.append((habit, uh.id in completed_ids))
        return result

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
