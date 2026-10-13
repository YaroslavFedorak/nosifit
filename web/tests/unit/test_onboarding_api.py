"""Onboarding API: profile, goals, injuries and completion."""

import pytest

from backend.app.extensions import db
from backend.app.models.injury import Injury
from backend.app.models.recovery.habit import RecoveryHabit
from backend.app.models.recovery.user_habit import UserRecoveryHabit
from backend.app.models.user_goals import UserTrainingGoals
from backend.app.models.user_injury import UserInjury
from backend.app.models.user_profile import UserProfile

ROUTES = ("/api/onboarding/profile", "/api/onboarding/goals", "/api/onboarding/injuries", "/api/onboarding/complete")


def login(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})


def profile_of(user):
    db.session.expire_all()
    return UserProfile.query.filter_by(user_id=user.id).first()


def test_profile_is_created_then_updated(client, user):
    login(client, user)

    created = client.post(
        "/api/onboarding/profile",
        json={"training_location": " GYM ", "wants_nutrition": True, "wants_recovery": "yes"},
    )
    assert created.status_code == 200
    # Choices are normalised; only a literal true enables a module.
    assert created.get_json() == {"training_location": "gym", "wants_nutrition": True, "wants_recovery": False}

    updated = client.post("/api/onboarding/profile", json={"wants_recovery": True})
    assert updated.get_json() == {"training_location": "home", "wants_nutrition": False, "wants_recovery": True}
    assert UserProfile.query.filter_by(user_id=user.id).count() == 1


def test_profile_rejects_a_malformed_location(client, user):
    login(client, user)
    client.post("/api/onboarding/profile", json={"training_location": "gym", "wants_nutrition": True})

    response = client.post("/api/onboarding/profile", json={"training_location": "gym; drop", "wants_nutrition": False})

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_input"}
    profile = profile_of(user)
    assert (profile.training_location, profile.wants_nutrition) == ("gym", True)


def test_goals_are_created_then_updated(client, user):
    login(client, user)

    created = client.post(
        "/api/onboarding/goals",
        json={"primary_goal": "Strength", "focus_upper": 7, "focus_lower": "3", "focus_core": 10},
    )
    assert created.status_code == 200
    assert created.get_json() == {"primary_goal": "strength", "focus_upper": 7, "focus_lower": 3, "focus_core": 10}

    updated = client.post(
        "/api/onboarding/goals", json={"primary_goal": "endurance", "focus_upper": 0, "focus_lower": 0, "focus_core": 0}
    )
    assert updated.get_json() == {"primary_goal": "endurance", "focus_upper": 0, "focus_lower": 0, "focus_core": 0}
    assert UserTrainingGoals.query.filter_by(user_id=user.id).count() == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"primary_goal": ""},
        {"primary_goal": "strength", "focus_upper": 11},
        {"primary_goal": "strength", "focus_core": -1},
        {"primary_goal": "strength", "focus_lower": True},
        {"primary_goal": "strength", "focus_upper": "a lot"},
    ],
)
def test_invalid_goals_are_rejected(client, user, body):
    login(client, user)

    response = client.post("/api/onboarding/goals", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_input"}
    assert UserTrainingGoals.query.filter_by(user_id=user.id).count() == 0


def test_injuries_replace_the_previous_list(client, user):
    knee, back = Injury(name="Knee"), Injury(name="Back")
    db.session.add_all([knee, back])
    db.session.commit()
    login(client, user)

    assert client.post("/api/onboarding/injuries", json={"injuries": [knee.id, back.id]}).get_json() == {"status": "ok"}
    assert client.post("/api/onboarding/injuries", json={"injuries": [back.id]}).get_json() == {"status": "ok"}
    assert [row.injury_id for row in UserInjury.query.filter_by(user_id=user.id)] == [back.id]

    invalid = client.post("/api/onboarding/injuries", json={"injuries": [999999]})
    assert invalid.status_code == 400
    assert invalid.get_json() == {"error": "invalid_input"}
    assert [row.injury_id for row in UserInjury.query.filter_by(user_id=user.id)] == [back.id]


def test_completing_onboarding_adds_default_recovery_habits_when_wanted(client, user):
    db.session.add_all(
        [
            RecoveryHabit(slug="drink_water", name="Drink water", points=1),
            RecoveryHabit(slug="walk_30m", name="Walk 30 min", points=1),
            RecoveryHabit(slug="cold_shower", name="Cold shower", points=1),
        ]
    )
    db.session.commit()
    login(client, user)
    client.post("/api/onboarding/profile", json={"wants_recovery": True})

    response = client.post("/api/onboarding/complete")

    assert response.status_code == 200
    assert response.get_json() == {"onboarding_completed": True}
    assert profile_of(user).onboarding_completed is True
    habits = UserRecoveryHabit.query.filter_by(user_id=user.id).all()
    assert sorted(h.habit.slug for h in habits) == ["drink_water", "walk_30m"]


def test_completing_onboarding_without_recovery_adds_no_habits(client, user):
    db.session.add(RecoveryHabit(slug="drink_water", name="Drink water", points=1))
    db.session.commit()
    login(client, user)

    assert client.post("/api/onboarding/complete").get_json() == {"onboarding_completed": True}
    assert profile_of(user).onboarding_completed is True
    assert UserRecoveryHabit.query.filter_by(user_id=user.id).count() == 0


@pytest.mark.parametrize("path", ROUTES)
def test_guests_are_sent_to_login(client, user, path):
    response = client.post(path, json={})

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert profile_of(user) is None
