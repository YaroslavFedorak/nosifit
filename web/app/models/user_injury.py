from web.app import db


class UserInjury(db.Model):
    __tablename__ = "user_injuries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    injury_id = db.Column(db.Integer, db.ForeignKey("injuries.id"), nullable=False)

    notes = db.Column(db.String(256))

    injury = db.relationship("Injury")
    user = db.relationship("User", backref="injuries")
