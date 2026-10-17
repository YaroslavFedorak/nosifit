"""add user consent

Revision ID: e4b8c2d6f1a3
Revises: b7d2e4a8c1f6
Create Date: 2026-10-18 10:00:00.000000

Three nullable columns on users; no existing row is changed. Existing users
have no recorded consent and are asked for it on their next request
(auth/consent.py). Downgrade drops the columns and the recorded consents.
"""
from alembic import op
import sqlalchemy as sa


revision = "e4b8c2d6f1a3"
down_revision = "b7d2e4a8c1f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("health_data_consent_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("consent_version", sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column("users", "consent_version")
    op.drop_column("users", "health_data_consent_at")
    op.drop_column("users", "privacy_accepted_at")
