from backend.app.extensions import db


class ProductFavorite(db.Model):
    __tablename__ = "nutrition_product_favorites"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_products.id"),
        nullable=False,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False,
    )

    user = db.relationship(
        "User",
        back_populates="nutrition_favorites",
    )

    product = db.relationship(
        "Product",
        back_populates="favorites",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_nutrition_product_favorite",
        ),
    )
