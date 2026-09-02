from web.app import db


class FatigueState(db.Model):
    __tablename__ = "te_fatigue_state"

    id = db.Column(db.Integer, primary_key=True)

    sleep = db.Column(db.Float, default=7.0)
    stress = db.Column(db.Integer, default=0)
    soreness = db.Column(db.Integer, default=0)
    hydration = db.Column(db.Float, default=2.0)

    user = db.relationship("User", back_populates="fatigue_state", uselist=False)
