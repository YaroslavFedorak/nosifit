from backend.app.extensions import db


class ProductName(db.Model):
    __tablename__ = "nutrition_product_names"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_products.id"),
        nullable=False,
        index=True,
    )

    locale = db.Column(
        db.String(10),
        nullable=False,
        index=True,
    )

    name = db.Column(
        db.String(160),
        nullable=False,
        index=True,
    )

    product = db.relationship(
        "Product",
        back_populates="names",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "product_id",
            "locale",
            name="uq_nutrition_product_name_locale",
        ),
    )

    def __repr__(self):
        return f"<ProductName product_id={self.product_id} locale={self.locale}>"
