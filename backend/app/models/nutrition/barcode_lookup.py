from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from backend.app.extensions import db


class BarcodeLookup(db.Model):
    """Cached answer of the external product database for one barcode.

    Only confirmed answers are stored: ``found`` (with the whitelisted raw
    fields in ``payload``) or ``not_found``. Timeouts, rate limits and
    malformed responses are never cached, so a temporary outage is not
    remembered as a missing product.

    ``payload`` is the external data as received, not trusted values: it is
    validated again every time it is read, and nothing in it is used for
    nutrition calculations until it is imported into ``nutrition_products``.
    Rows expire (``expires_at``) and expired rows are purged, so the table
    stays bounded.
    """

    __tablename__ = "nutrition_barcode_lookups"

    # Canonical GTIN (see services.nutrition.barcode).
    barcode = db.Column(db.String(14), primary_key=True)

    # Which database answered, e.g. ``open_food_facts``.
    provider = db.Column(db.String(32), nullable=False)

    # ``found`` | ``not_found``
    status = db.Column(db.String(16), nullable=False)

    payload = db.Column(JSONB, nullable=True)

    fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('found', 'not_found')",
            name="ck_nutrition_barcode_lookups_status",
        ),
    )

    def __repr__(self):
        return f"<BarcodeLookup {self.barcode} {self.status}>"
