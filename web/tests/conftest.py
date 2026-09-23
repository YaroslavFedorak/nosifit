import pytest
from backend.app.extensions import db
from web.app import create_app
from backend.app.models.user import User
from werkzeug.security import generate_password_hash


TEST_DATABASE_URI = "postgresql+psycopg://postgres:postgres123@localhost:5432/nosifit_test"


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
