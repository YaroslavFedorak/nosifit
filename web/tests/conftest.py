import os
import secrets

import pytest
from dotenv import load_dotenv
from flask_migrate import upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.user import User
from web.app import create_app

load_dotenv()

_BASE_DATABASE_URI = os.getenv("TEST_DATABASE_URL")

if not _BASE_DATABASE_URI:
    raise RuntimeError("TEST_DATABASE_URL is not configured")

# Same driver rule as backend/config.py: plain postgresql:// means psycopg 3.
for _prefix in ("postgres://", "postgresql://"):
    if _BASE_DATABASE_URI.startswith(_prefix):
        _BASE_DATABASE_URI = "postgresql+psycopg://" + _BASE_DATABASE_URI[len(_prefix):]

# The suite truncates every table: refuse anything that is not a test database.
if "test" not in (make_url(_BASE_DATABASE_URI).database or ""):
    raise RuntimeError("TEST_DATABASE_URL must point at a database whose name contains 'test'")

# Each run gets its own schema, so parallel runs never share tables.
TEST_SCHEMA = f"test_{os.getpid()}_{secrets.token_hex(3)}"
TEST_DATABASE_URI = (
    make_url(_BASE_DATABASE_URI)
    .update_query_dict({"options": f"-csearch_path={TEST_SCHEMA},public"})
    .render_as_string(hide_password=False)
)

# Filled once per run by the migrations, not by db.create_all(), so tests use
# the same schema as production.
_KEEP_TABLES = {"alembic_version"}


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    engine = create_engine(_BASE_DATABASE_URI)
    with engine.begin() as conn:
        # In public, so dropping the run's schema never drops the extension
        # another run is using.
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public"))
        conn.execute(text(f'CREATE SCHEMA "{TEST_SCHEMA}"'))

    migrated = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URI})
    with migrated.app_context():
        upgrade(directory=os.path.join(os.path.dirname(__file__), "..", "..", "migrations"))
        db.engine.dispose()

    yield TEST_SCHEMA

    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{TEST_SCHEMA}" CASCADE'))
    engine.dispose()


def _truncate_all():
    tables = [
        name
        for (name,) in db.session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = :schema"),
            {"schema": TEST_SCHEMA},
        )
        if name not in _KEEP_TABLES
    ]
    if tables:
        names = ", ".join(f'"{TEST_SCHEMA}"."{name}"' for name in tables)
        db.session.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        db.session.commit()


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URI,
        }
    )

    with app.app_context():
        _truncate_all()
        yield app
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(
        username="testuser",
        email="test@example.com",
        password=generate_password_hash("password123"),
    )
    db.session.add(u)
    db.session.commit()
    return u


class FakeBotAuthClient:
    """The web app as the Telegram bot's session restore sees it.

    Tests never let telegram_bot.runtime reach a real web app (the developer's
    .env may point it at one). Mirrors /api/telegram/login (restore) and
    /api/telegram/logout: linked ids restore unless logged out in the bot.
    """

    def __init__(self):
        self.linked = set()
        self.logged_out = set()
        self.restore_calls = []
        self.logout_calls = []

    def restore(self, telegram_user_id):
        from telegram_bot.services.api import NosiFitAPI
        from telegram_bot.services.telegram_auth import TelegramAuthError

        self.restore_calls.append(telegram_user_id)
        if telegram_user_id not in self.linked:
            raise TelegramAuthError("not_linked", "not_linked")
        if telegram_user_id in self.logged_out:
            raise TelegramAuthError("logged_out", "logged_out")
        api = NosiFitAPI(base_url="http://test")
        api.session.cookies.set("session", f"restored-{telegram_user_id}")
        return api

    def logout(self, telegram_user_id):
        self.logout_calls.append(telegram_user_id)
        if telegram_user_id in self.linked:
            self.logged_out.add(telegram_user_id)


@pytest.fixture(autouse=True)
def bot_auth(monkeypatch):
    from telegram_bot import runtime

    fake = FakeBotAuthClient()
    monkeypatch.setattr(runtime, "auth_client", lambda: fake)
    runtime._no_restore.clear()
    yield fake
    runtime._no_restore.clear()
