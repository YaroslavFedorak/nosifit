"""The models describe exactly the schema the migrations build.

Production runs ``flask db upgrade``; the test suite runs on the same
migrated schema (see conftest). A model change without a migration, or a
migration the models do not reflect, shows up here.
"""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from backend.app.extensions import db


def test_models_match_the_migrated_schema(app):
    with db.engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), db.metadata)

    assert diff == []
