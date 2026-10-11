import pytest
from sqlalchemy import text
from backend.app.extensions import db
from web.app import create_app
from backend.app.models.user import User
from werkzeug.security import generate_password_hash

import os
from dotenv import load_dotenv

load_dotenv()

TEST_DATABASE_URI = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URI:
    raise RuntimeError("TEST_DATABASE_URL is not configured")


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URI,
        }
    )

    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        db.session.commit()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


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
