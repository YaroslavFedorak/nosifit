from web.app import db


class RecoveryPlan(db.Model):
    __tablename__ = "recovery_plans"

    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
