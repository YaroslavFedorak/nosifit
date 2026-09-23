import pytest
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
