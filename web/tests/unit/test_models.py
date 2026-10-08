from backend.app.models.user import User
from backend.app.extensions import db


def test_create_user(app):
    user = User(
        username="yarik",
        email="model@example.com",
        password="hashedpass",
    )

    db.session.add(user)
    db.session.commit()

    saved = User.query.filter_by(email="model@example.com").first()

    assert saved is not None
    assert saved.username == "yarik"
    assert saved.password == "hashedpass"
