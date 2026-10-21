"""strip exercise-id keys from training_sessions.muscle_loads

Before the v2 training model the column held {exercise_id: load}. It now
holds {muscle_slug: effective_sets}. Keys that are not muscle slugs are
removed; sessions left empty can be rebuilt from their logged exercises with
``python -m web.scripts.rebuild_muscle_loads``. Not reversible: the dropped
values were never meaningful as muscle loads.

Revision ID: f2b8d6a4c0e1
Revises: a7c3e9d1f4b6
Create Date: 2026-10-21
"""

import json

import sqlalchemy as sa
from alembic import op

from backend.app.training.exercises.catalog import known_muscle_slugs

revision = "f2b8d6a4c0e1"
down_revision = "a7c3e9d1f4b6"
branch_labels = None
depends_on = None


def _clean(value, known):
    if not isinstance(value, dict):
        return {}
    return {key: load for key, load in value.items() if key in known}


def upgrade():
    bind = op.get_bind()
    known = known_muscle_slugs()
    sessions = sa.table(
        "training_sessions",
        sa.column("id", sa.Integer),
        sa.column("muscle_loads", sa.JSON),
    )

    rows = bind.execute(
        sa.select(sessions.c.id, sessions.c.muscle_loads).where(
            sessions.c.muscle_loads.isnot(None)
        )
    ).fetchall()

    for session_id, value in rows:
        if isinstance(value, str):
            value = json.loads(value)
        cleaned = _clean(value, known)
        if cleaned != value:
            bind.execute(
                sessions.update()
                .where(sessions.c.id == session_id)
                .values(muscle_loads=cleaned)
            )


def downgrade():
    pass
