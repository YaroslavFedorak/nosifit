"""Injuries API: the catalog and the signed-in user's injuries."""

import pytest

from backend.app.extensions import db
from backend.app.models.injury import Injury
from backend.app.models.user_injury import UserInjury


@pytest.fixture
def injuries(app):
    rows = [Injury(name="Knee", description="Knee pain"), Injury(name="Shoulder", description=None)]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def login(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})


def user_injury_ids(user):
    return sorted(row.injury_id for row in UserInjury.query.filter_by(user_id=user.id))


def test_catalog_is_listed_without_signing_in(client, injuries):
    response = client.get("/api/injuries/")

    assert response.status_code == 200
    assert response.get_json() == [
        {"id": injuries[0].id, "name": "Knee", "description": "Knee pain"},
        {"id": injuries[1].id, "name": "Shoulder", "description": None},
    ]


def test_saving_replaces_the_users_injuries(client, user, injuries):
    knee, shoulder = (row.id for row in injuries)
    login(client, user)

    first = client.post("/api/injuries/user", json={"injuries": [knee, knee, shoulder]})
    assert first.status_code == 200
    assert first.get_json() == {"status": "ok"}
    assert user_injury_ids(user) == sorted([knee, shoulder])

    second = client.post("/api/injuries/user", json={"injuries": [shoulder]})
    assert second.get_json() == {"status": "ok"}
    assert user_injury_ids(user) == [shoulder]

    cleared = client.post("/api/injuries/user", json={"injuries": []})
    assert cleared.get_json() == {"status": "ok"}
    assert user_injury_ids(user) == []


@pytest.mark.parametrize("body", [{"injuries": [999999]}, {"injuries": [True]}, {"injuries": "1"}])
def test_invalid_injuries_are_rejected(client, user, injuries, body):
    login(client, user)

    response = client.post("/api/injuries/user", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_input"}
    assert user_injury_ids(user) == []


def test_guests_cannot_save_injuries(client, user, injuries):
    response = client.post("/api/injuries/user", json={"injuries": [injuries[0].id]})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert UserInjury.query.count() == 0
