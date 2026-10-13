"""Equipment API: the signed-in user's available equipment."""

import pytest

from backend.app.extensions import db
from backend.app.models.user_equipment import UserEquipment
from backend.app.training.models.equipment import TEEquipment


@pytest.fixture
def equipment(app):
    rows = [TEEquipment(slug="barbell", name="Barbell"), TEEquipment(slug="dumbbells", name="Dumbbells")]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def login(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})


def owned_ids(user):
    return sorted(row.equipment_id for row in UserEquipment.query.filter_by(user_id=user.id))


def test_adding_listing_and_removing_equipment(client, user, equipment):
    barbell, dumbbells = equipment
    login(client, user)

    assert client.get("/api/user/equipment/").get_json() == []

    added = client.post("/api/user/equipment/add", json={"equipment_id": barbell.id})
    assert added.status_code == 200
    assert added.get_json() == {"status": "added"}
    # A numeric string is accepted; adding twice keeps one row.
    assert client.post("/api/user/equipment/add", json={"equipment_id": str(dumbbells.id)}).status_code == 200
    assert client.post("/api/user/equipment/add", json={"equipment_id": barbell.id}).status_code == 200
    assert owned_ids(user) == sorted([barbell.id, dumbbells.id])

    listed = client.get("/api/user/equipment/")
    assert listed.status_code == 200
    assert sorted(item["slug"] for item in listed.get_json()) == ["barbell", "dumbbells"]
    assert set(listed.get_json()[0]) == {"id", "slug", "name", "tags", "description"}

    removed = client.post("/api/user/equipment/remove", json={"equipment_id": barbell.id})
    assert removed.status_code == 200
    assert removed.get_json() == {"status": "removed"}
    assert owned_ids(user) == [dumbbells.id]


@pytest.mark.parametrize("value", [999999, True, "abc", 0, -1, None])
def test_unknown_or_invalid_equipment_is_not_added(client, user, equipment, value):
    login(client, user)

    response = client.post("/api/user/equipment/add", json={"equipment_id": value})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert owned_ids(user) == []


@pytest.mark.parametrize("value", [True, "abc", 0, None])
def test_invalid_equipment_id_cannot_be_removed(client, user, equipment, value):
    login(client, user)

    response = client.post("/api/user/equipment/remove", json={"equipment_id": value})

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_input"}


@pytest.mark.parametrize(
    "method, path",
    [("get", "/api/user/equipment/"), ("post", "/api/user/equipment/add"), ("post", "/api/user/equipment/remove")],
)
def test_guests_are_sent_to_login(client, user, equipment, method, path):
    response = getattr(client, method)(path, json={"equipment_id": equipment[0].id})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert UserEquipment.query.count() == 0
