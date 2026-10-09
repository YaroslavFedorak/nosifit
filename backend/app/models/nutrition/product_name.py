from sqlalchemy.orm import validates

from backend.app.extensions import db
from backend.app.utils.name_normalization import normalize_name


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

    # Lowercase, punctuation-folded form of ``name`` that search runs on.
    normalized_name = db.Column(
        db.String(160),
        nullable=False,
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
        # Prefix search: ``normalized_name LIKE 'q%'``.
        db.Index(
            "ix_nutrition_product_names_normalized_prefix",
            "normalized_name",
            postgresql_ops={"normalized_name": "text_pattern_ops"},
        ),
        # Substring and typo-tolerant search.
        db.Index(
            "ix_nutrition_product_names_normalized_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
    )

    @validates("name")
    def _sync_normalized_name(self, _key, value):
        # Kept in step with ``name`` on every write, whoever writes it.
        self.normalized_name = normalize_name(value)[:160]
        return value

    def __repr__(self):
        return f"<ProductName product_id={self.product_id} locale={self.locale}>"
