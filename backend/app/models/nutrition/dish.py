from datetime import datetime

from backend.app.extensions import db


class Dish(db.Model):
    """A user's reusable dish: a named list of products with amounts.

    A dish is a template. Logging it copies its components into meal entries
    with their own nutrition snapshot; neither side changes the other later.
    """

    __tablename__ = "nutrition_dishes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = db.Column(db.String(120), nullable=False)
    normalized_name = db.Column(db.String(160), nullable=False)

    use_count = db.Column(db.Integer, nullable=False, default=0)
    last_used_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship("User", back_populates="nutrition_dishes")

    items = db.relationship(
        "DishItem",
        back_populates="dish",
        cascade="all, delete-orphan",
        order_by="DishItem.position",
        lazy="selectin",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_nutrition_dishes_user_name",
        ),
        # "Recent dishes" list.
        db.Index(
            "ix_nutrition_dishes_user_last_used",
            "user_id",
            db.text("last_used_at DESC NULLS LAST"),
        ),
    )

    def __repr__(self):
        return f"<Dish id={self.id} user_id={self.user_id} name={self.name}>"


class DishItem(db.Model):
    __tablename__ = "nutrition_dish_items"

    id = db.Column(db.Integer, primary_key=True)

    dish_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_dishes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Products are archived, never deleted, so a dish never loses a component.
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(8), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    dish = db.relationship("Dish", back_populates="items")
    product = db.relationship("Product")

    __table_args__ = (
        # One line per product; adding the same product again changes its amount.
        db.UniqueConstraint(
            "dish_id",
            "product_id",
            name="uq_nutrition_dish_items_dish_product",
        ),
        db.CheckConstraint("amount > 0", name="ck_nutrition_dish_items_amount_positive"),
    )

    def __repr__(self):
        return f"<DishItem dish_id={self.dish_id} product_id={self.product_id}>"
