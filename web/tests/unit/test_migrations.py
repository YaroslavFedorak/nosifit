import os

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations")
)


def test_migrations_have_a_single_head():
    # Two branches that each add a migration on top of the same revision
    # leave Alembic with several heads, and `flask db upgrade` (the Railway
    # pre-deploy command) then refuses to run. Add a merge revision instead.
    config = Config()
    config.set_main_option("script_location", MIGRATIONS_DIR)

    heads = ScriptDirectory.from_config(config).get_heads()

    assert len(heads) == 1, f"multiple migration heads: {heads}"
