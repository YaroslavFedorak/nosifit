"""exercise measurement type, load type and prescription; session durations

Revision ID: b7e2d4f1a9c3
Revises: a9c3e5f7b1d2
Create Date: 2026-10-08 12:00:00

Exercises now declare whether they are prescribed in repetitions or in
seconds. Session rows get dedicated duration columns, so seconds are no
longer stored in the reps columns.

Before this revision the load engine treated a fixed list of slugs as timed
exercises and read their reps value as seconds; for those slugs the values
are moved into the duration columns. Other exercises that became
duration-based had no such convention, so their historical reps values are
left untouched, and repetition exercises are never touched at all.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7e2d4f1a9c3"
down_revision = "a9c3e5f7b1d2"
branch_labels = None
depends_on = None

# TIME_BASED_EXERCISES from the pre-revision load engine.
LEGACY_TIMED_SLUGS = (
    "plank",
    "side-plank",
    "wall-sit",
    "dead-hang",
    "hollow-hold",
    "glute-bridge-hold",
)


def upgrade():
    with op.batch_alter_table("te_exercises") as batch_op:
        batch_op.add_column(
            sa.Column(
                "measurement_type",
                sa.String(length=16),
                nullable=False,
                server_default="reps",
            )
        )
        batch_op.add_column(sa.Column("load_type", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("bodyweight_ratio", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "prescription",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            )
        )

    with op.batch_alter_table("session_exercises") as batch_op:
        batch_op.add_column(
            sa.Column("duration_sec_planned", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("duration_sec_done", sa.Integer(), nullable=True))

    slugs = sa.bindparam("slugs", value=list(LEGACY_TIMED_SLUGS), expanding=True)

    op.get_bind().execute(
        sa.text(
            "UPDATE te_exercises SET measurement_type = 'duration' "
            "WHERE slug IN :slugs"
        ).bindparams(slugs)
    )

    op.get_bind().execute(
        sa.text(
            """
            UPDATE session_exercises AS se
            SET duration_sec_done = CAST(
                    substring(se.reps_done FROM '^\\s*([0-9]{1,4})') AS INTEGER
                ),
                duration_sec_planned = CAST(
                    substring(se.reps_planned FROM '^\\s*([0-9]{1,4})') AS INTEGER
                ),
                reps_done = NULL,
                reps_planned = NULL
            FROM te_exercises AS ex
            WHERE se.exercise_id = ex.id
              AND ex.slug IN :slugs
            """
        ).bindparams(slugs)
    )


def downgrade():
    slugs = sa.bindparam("slugs", value=list(LEGACY_TIMED_SLUGS), expanding=True)

    op.get_bind().execute(
        sa.text(
            """
            UPDATE session_exercises AS se
            SET reps_done = CAST(se.duration_sec_done AS VARCHAR),
                reps_planned = CAST(se.duration_sec_planned AS VARCHAR)
            FROM te_exercises AS ex
            WHERE se.exercise_id = ex.id
              AND ex.slug IN :slugs
            """
        ).bindparams(slugs)
    )

    with op.batch_alter_table("session_exercises") as batch_op:
        batch_op.drop_column("duration_sec_done")
        batch_op.drop_column("duration_sec_planned")

    with op.batch_alter_table("te_exercises") as batch_op:
        batch_op.drop_column("prescription")
        batch_op.drop_column("bodyweight_ratio")
        batch_op.drop_column("load_type")
        batch_op.drop_column("measurement_type")
