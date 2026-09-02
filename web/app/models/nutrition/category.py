from web.app import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )

    name = db.Column(db.String(50), nullable=False)

    items = db.relationship("MealItem", backref="category", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"
