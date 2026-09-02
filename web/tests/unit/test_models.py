from web.app.models.user import User
from web.app import db


def test_create_user(app):
    user = User(username="yarik", email="test@example.com", password="hashedpass")
    db.session.add(user)
    db.session.commit()

    saved = User.query.filter_by(email="test@example.com").first()

    assert saved is not None
    assert saved.username == "yarik"
    assert saved.password == "hashedpass"
