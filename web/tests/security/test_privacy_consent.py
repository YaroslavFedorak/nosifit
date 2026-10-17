"""Privacy policy page and the consent gate (auth/consent.py)."""

from datetime import datetime

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from backend.app.extensions import db
from backend.app.models.oauth_account import OAuthAccount
from backend.app.models.telegram import TelegramIdentity
from backend.app.models.user import User
from backend.app.models.verification_code import VerificationCode
from backend.app.services.consent import CONSENT_VERSION, has_current_consent

PASSWORD = "password123"
BOTH = {"privacy_consent": "on", "health_consent": "on", "age_confirmed": "on"}


@pytest.fixture
def plain_user(app, no_auto_consent):
    """A user as every existing account is right after the deploy: no consent."""
    u = User(
        username="plain",
        email="plain@example.com",
        password=generate_password_hash(PASSWORD),
        privacy_accepted_at=None,
    )
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, email="plain@example.com"):
    response = client.post("/auth/login", data={"email": email, "password": PASSWORD})
    g.pop("_login_user", None)
    return response


def _get(client, path, **kwargs):
    g.pop("_login_user", None)
    return client.get(path, **kwargs)


def _post(client, path, **kwargs):
    g.pop("_login_user", None)
    return client.post(path, **kwargs)


# --- /privacy ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "locale, heading",
    [("uk", "Політика конфіденційності NosiFit"), ("en", "NosiFit Privacy Policy"), ("pl", "NosiFit Privacy Policy"), ("ru", "NosiFit Privacy Policy")],
)
def test_privacy_page_is_public_in_every_language(app, client, locale, heading):
    app.config.update(PRIVACY_CONTROLLER_NAME="Jane Owner", PRIVACY_CONTACT_EMAIL="privacy@example.com")
    client.set_cookie("nosifit_locale", locale)

    response = client.get("/privacy")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert heading in text
    assert "Jane Owner" in text and "mailto:privacy@example.com" in text
    assert CONSENT_VERSION in text


def test_privacy_page_marks_missing_controller_details(app, client):
    app.config.update(PRIVACY_CONTROLLER_NAME="", PRIVACY_CONTACT_EMAIL="")
    client.set_cookie("nosifit_locale", "uk")

    text = client.get("/privacy").get_data(as_text=True)

    assert "володільця не вказано]" in text and "[email не вказано]" in text


def test_links_to_the_policy_resolve(client):
    register = client.get("/auth/register").get_data(as_text=True)
    assert 'href="/privacy"' in register
    assert 'name="privacy_consent"' in register and 'name="health_consent"' in register
    assert client.get("/privacy").status_code == 200


# --- The gate ---------------------------------------------------------------------


def test_pages_redirect_to_consent_and_back(client, plain_user):
    _login(client)

    response = _get(client, "/dashboard/")

    assert response.status_code == 302
    assert response.location.startswith("/consent?next=/dashboard/")


@pytest.mark.parametrize("path", ["/api/nutrition/day", "/api/v1/nutrition/day"])
def test_api_answers_consent_required(client, plain_user, path):
    _login(client)

    response = _get(client, path)

    assert response.status_code == 403
    assert response.get_json()["code"] == "consent_required"


def test_writes_are_refused_without_consent(client, plain_user):
    _login(client)

    water = _post(client, "/api/nutrition/water", json={"amount": 0.5})
    profile = _post(client, "/profile/update_full", json={"weight": 80})

    assert water.status_code == 403 and water.get_json()["code"] == "consent_required"
    assert profile.status_code == 403


def test_what_stays_open_without_consent(client, plain_user):
    _login(client)

    assert _get(client, "/privacy").status_code == 200
    assert _get(client, "/consent").status_code == 200
    assert _get(client, "/healthz").status_code == 200
    assert _get(client, "/").status_code in (200, 302)
    assert _get(client, "/consent").status_code == 200
    # Deleting the account is never blocked by the gate.
    delete = _post(client, "/profile/delete/request", json={})
    assert not (delete.status_code == 403 and (delete.get_json() or {}).get("code") == "consent_required")
    assert _get(client, "/auth/logout").status_code == 302


def test_anonymous_visitors_are_not_affected(client, no_auto_consent):
    assert client.get("/dashboard/").location.startswith("/auth/login")
    assert client.get("/api/nutrition/day").status_code == 401


# --- Giving consent -------------------------------------------------------------


@pytest.mark.parametrize(
    "partial",
    [
        {},
        {"privacy_consent": "on"},
        {"health_consent": "on"},
        {"privacy_consent": "on", "health_consent": "on"},  # no age confirmation
        {"age_confirmed": "on", "health_consent": "on"},
    ],
)
def test_both_consents_and_the_age_are_required(client, plain_user, partial):
    _login(client)

    _post(client, "/consent", data={**partial, "next": "/dashboard/"})

    db.session.refresh(plain_user)
    assert not has_current_consent(plain_user)
    assert plain_user.privacy_accepted_at is None and plain_user.health_data_consent_at is None


def test_consent_is_recorded_and_unlocks_the_app(client, plain_user):
    _login(client)

    response = _post(client, "/consent", data={**BOTH, "next": "/dashboard/"})

    assert response.status_code == 302 and response.location == "/dashboard/"
    db.session.refresh(plain_user)
    assert has_current_consent(plain_user)
    assert plain_user.consent_version == CONSENT_VERSION
    assert isinstance(plain_user.health_data_consent_at, datetime)
    assert _get(client, "/dashboard/").status_code == 200
    assert _get(client, "/api/nutrition/day").status_code == 200


@pytest.mark.parametrize("target", ["//evil.example/x", "https://evil.example/", "/\\evil.example"])
def test_consent_never_redirects_off_site(client, plain_user, target):
    _login(client)

    response = _post(client, "/consent", data={**BOTH, "next": target})

    assert response.location == "/dashboard/"


def test_a_new_policy_version_asks_again(client, plain_user):
    plain_user.privacy_accepted_at = plain_user.health_data_consent_at = datetime.utcnow()
    plain_user.consent_version = "2000-01-01"
    db.session.commit()
    _login(client)

    assert _get(client, "/api/nutrition/day").get_json()["code"] == "consent_required"


def test_consent_api(client, plain_user):
    assert client.post("/api/consent", json=BOTH).status_code == 401
    _login(client)

    missing = _post(client, "/api/consent", json={"privacy_consent": True})
    assert missing.status_code == 400 and missing.get_json()["code"] == "consent_missing"

    no_age = _post(client, "/api/consent", json={"privacy_consent": True, "health_consent": True})
    assert no_age.status_code == 400 and no_age.get_json()["code"] == "consent_missing"

    given = _post(
        client,
        "/api/v1/consent",
        json={"privacy_consent": True, "health_consent": True, "age_confirmed": True},
    )
    assert given.status_code == 200 and given.get_json()["consent_version"] == CONSENT_VERSION
    db.session.refresh(plain_user)
    assert has_current_consent(plain_user)


def test_telegram_session_can_give_consent_and_is_otherwise_stopped(client, plain_user):
    identity = TelegramIdentity(user_id=plain_user.id, telegram_user_id=4242)
    db.session.add(identity)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = plain_user.get_id()
        session["_fresh"] = True
        session["tg_identity"] = identity.id

    blocked = _get(client, "/api/nutrition/day")
    assert blocked.status_code == 403 and blocked.get_json()["code"] == "consent_required"

    given = _post(
        client, "/api/consent", json={"privacy_consent": True, "health_consent": True, "age_confirmed": True}
    )
    assert given.status_code == 200
    assert _get(client, "/api/nutrition/day").status_code == 200


# --- Registration -----------------------------------------------------------------


@pytest.fixture
def sent_codes(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "web.app.routes.auth.email_verification.send_verification_email",
        lambda email, code: sent.append((email, code)),
    )
    return sent


FORM = {
    "username": "newbie",
    "email": "newbie@example.com",
    "password": "a-good-password",
    "confirm_password": "a-good-password",
    "weight": "80",
    "height": "180",
    "age": "30",
}


@pytest.mark.parametrize("partial", [{}, {"privacy_consent": "on"}, {"health_consent": "on"}])
def test_registration_without_both_consents_keeps_nothing(client, no_auto_consent, sent_codes, partial):
    response = client.post("/verify/send_code", data={**FORM, **partial})

    assert response.location.endswith("/auth/register")
    assert sent_codes == []
    assert VerificationCode.query.count() == 0
    with client.session_transaction() as session:
        assert "reg_data" not in session  # no weight/height/age kept


def test_registration_records_consent(client, no_auto_consent, sent_codes):
    client.post("/verify/send_code", data={**FORM, **BOTH})
    client.post("/verify/verify_email", data={"code": sent_codes[0][1]})
    response = client.post("/auth/register_complete", data={})

    assert response.location.endswith("/dashboard/")
    user = User.query.filter_by(email="newbie@example.com").one()
    assert has_current_consent(user)
    g.pop("_login_user", None)
    assert client.get("/dashboard/").status_code == 200  # no second consent screen


def test_registration_session_without_consent_cannot_complete(client, no_auto_consent):
    with client.session_transaction() as session:
        session["reg_data"] = {"username": "x", "email": "x@example.com", "password_hash": "h"}
        session["verified_email"] = "x@example.com"

    client.post("/auth/register_complete", data={})

    assert User.query.filter_by(email="x@example.com").first() is None


def _oauth_session(client, uid):
    with client.session_transaction() as session:
        session["oauth_user"] = {
            "provider": "github",
            "provider_user_id": uid,
            "username": "octo",
            "email": f"octo{uid}@example.com",
        }


PROFILE = {"age": "25", "height": "180", "weight": "75", "workouts": "3"}


def test_oauth_profile_without_consent_creates_nothing(client, no_auto_consent):
    _oauth_session(client, "901")

    response = client.post("/auth/complete_profile", data={**PROFILE, "privacy_consent": "on"})

    assert response.status_code == 200
    assert OAuthAccount.query.filter_by(provider_user_id="901").first() is None
    assert User.query.filter_by(email="octo901@example.com").first() is None


def test_oauth_profile_records_consent(client, no_auto_consent):
    _oauth_session(client, "902")

    response = client.post("/auth/complete_profile", data={**PROFILE, **BOTH})

    assert response.status_code == 302
    user = User.query.filter_by(email="octo902@example.com").one()
    assert has_current_consent(user)


# --- Minimum age: 16 --------------------------------------------------------------


def test_account_age_parser():
    from backend.app.utils.validation import ValidationError, parse_account_age

    assert parse_account_age("16") == 16 and parse_account_age("") is None
    for bad in ("15", "10", "16.5", "-1", "abc"):
        with pytest.raises(ValidationError):
            parse_account_age(bad)
    with pytest.raises(ValidationError):
        parse_account_age("", required=True)


@pytest.mark.parametrize("age", ["15", "", "10"])
def test_registration_needs_age_16(client, no_auto_consent, sent_codes, age):
    response = client.post("/verify/send_code", data={**FORM, **BOTH, "age": age})

    assert response.location.endswith("/auth/register")
    assert sent_codes == []
    with client.session_transaction() as session:
        assert "reg_data" not in session


def test_registration_at_16_works(client, no_auto_consent, sent_codes):
    client.post("/verify/send_code", data={**FORM, **BOTH, "age": "16"})
    client.post("/verify/verify_email", data={"code": sent_codes[0][1]})
    client.post("/auth/register_complete", data={})

    assert User.query.filter_by(email="newbie@example.com").one().profile.age == 16


def test_oauth_profile_needs_age_16(client, no_auto_consent):
    _oauth_session(client, "903")

    client.post("/auth/complete_profile", data={**PROFILE, **BOTH, "age": "15"})

    assert User.query.filter_by(email="octo903@example.com").first() is None


def test_profile_edit_rejects_age_under_16(client, user):
    from backend.app.models.user_profile import UserProfile

    db.session.add(UserProfile(user_id=user.id, training_location="home", age=30))
    db.session.commit()
    _login(client, "test@example.com")

    _post(client, "/profile/update_full", data={"username": "testuser", "age": "15"})
    db.session.refresh(user)
    assert user.profile.age == 30

    _post(client, "/profile/update_full", data={"username": "testuser", "age": "16"})
    db.session.refresh(user)
    assert user.profile.age == 16


@pytest.fixture
def young_user(plain_user):
    from backend.app.models.user_profile import UserProfile

    db.session.add(UserProfile(user_id=plain_user.id, training_location="home", age=14))
    db.session.commit()
    return plain_user


def test_consent_is_refused_when_the_profile_says_under_16(client, young_user):
    _login(client)

    page = _get(client, "/consent").get_data(as_text=True)
    _post(client, "/consent", data={**BOTH, "next": "/dashboard/"})
    api = _post(client, "/api/consent", json={"privacy_consent": True, "health_consent": True, "age_confirmed": True})

    assert "менше 16" in page and 'name="health_consent"' not in page
    assert api.status_code == 403 and api.get_json()["code"] == "under_minimum_age"
    db.session.refresh(young_user)
    assert not has_current_consent(young_user)
    # ...but their data stays theirs to take or delete.
    assert _get(client, "/privacy/my-data").status_code == 200
    assert _get(client, "/profile/").status_code == 200


# --- No loops, and data stays reachable without consent ---------------------------


@pytest.mark.parametrize(
    "path",
    ["/dashboard/", "/nutrition/", "/training/", "/recovery/", "/", "/consent", "/consent?next=/consent"],
)
def test_no_redirect_loop_without_consent(client, plain_user, path):
    _login(client)
    g.pop("_login_user", None)

    response = client.get(path, follow_redirects=True)

    assert response.status_code == 200
    assert len(response.history) <= 2
    assert response.request.path in ("/consent", "/", "/landing")


def test_declining_keeps_the_user_on_a_working_consent_page(client, plain_user):
    _login(client)

    response = _post(client, "/consent", data={"next": "/dashboard/"}, follow_redirects=True)

    assert response.status_code == 200 and len(response.history) == 1
    text = response.get_data(as_text=True)
    assert "/privacy/my-data" in text and "Вийти" in text and "Видалити акаунт" in text


def test_profile_page_and_account_deletion_work_without_consent(client, plain_user, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "web.app.routes.profile.delete_account_request.send_email_code",
        lambda email, code: sent.update(code=code),
    )
    user_id = plain_user.id
    _login(client)

    assert _get(client, "/profile/").status_code == 200
    _post(client, "/profile/delete/request")
    _post(client, "/profile/delete/confirm", json={"code": sent["code"]})
    final = _post(client, "/profile/delete/final", json={"email": "plain@example.com", "password": PASSWORD})

    assert final.get_json()["status"] == "deleted"
    db.session.expire_all()
    assert db.session.get(User, user_id) is None


def test_my_data_export(client, plain_user, app):
    from datetime import date

    from backend.app.models.nutrition.meal import Meal
    from backend.app.models.nutrition.meal_item import MealItem
    from backend.app.models.training_session import SessionExercise, TrainingSession

    other = User(username="other", email="other@example.com", password=generate_password_hash(PASSWORD))
    db.session.add(other)
    db.session.flush()
    mine = Meal(user_id=plain_user.id, date=date(2026, 6, 1), name="mine", category="lunch")
    theirs = Meal(user_id=other.id, date=date(2026, 6, 1), name="theirs", category="lunch")
    db.session.add_all([mine, theirs])
    db.session.flush()
    db.session.add_all([
        MealItem(meal_id=mine.id, name="my oats", calories=100),
        MealItem(meal_id=theirs.id, name="their oats", calories=100),
    ])
    session = TrainingSession(user_id=plain_user.id, status="done")
    db.session.add(session)
    db.session.flush()
    db.session.add(SessionExercise(session_id=session.id, exercise_id="bench_press"))
    db.session.commit()

    assert client.get("/privacy/my-data").status_code == 302  # signed in only
    _login(client)
    response = _get(client, "/privacy/my-data")

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"
    tables = response.get_json()["tables"]
    assert tables["users"][0]["email"] == "plain@example.com"
    assert "password" not in tables["users"][0]
    assert [m["name"] for m in tables["meals"]] == ["mine"]
    assert [i["name"] for i in tables["meal_items"]] == ["my oats"]
    assert len(tables["training_sessions"]) == 1 and len(tables["session_exercises"]) == 1
    body = response.get_data(as_text=True)
    assert "theirs" not in body and "their oats" not in body and "other@example.com" not in body


# --- Withdrawing consent ------------------------------------------------------------


@pytest.fixture
def rich_user(app):
    """A consented user with records in every kind of health data, plus another user."""
    from datetime import date, timezone

    from backend.app.models.nutrition.meal import Meal
    from backend.app.models.nutrition.meal_item import MealItem
    from backend.app.models.nutrition.user_water import UserWater
    from backend.app.models.nutrition.user_weight import UserWeight
    from backend.app.models.oauth_account import OAuthAccount
    from backend.app.models.recovery.sleep_entry import SleepEntry
    from backend.app.models.training_session import SessionExercise, TrainingSession
    from backend.app.models.user_profile import UserProfile
    from backend.app.training.models.fatigue_state import FatigueState

    def make(name):
        fatigue = FatigueState(sleep=6.5, stress=3)
        db.session.add(fatigue)
        db.session.flush()
        u = User(
            username=name,
            email=f"{name}@example.com",
            password=generate_password_hash(PASSWORD),
            age=30,
            weight=80.0,
            fatigue_state_id=fatigue.id,
        )
        db.session.add(u)
        db.session.flush()
        db.session.add(UserProfile(user_id=u.id, training_location="gym", age=30, weight=80, height=180))
        meal = Meal(user_id=u.id, date=date(2026, 6, 1), name=f"{name}-meal", category="lunch")
        db.session.add(meal)
        db.session.flush()
        db.session.add(MealItem(meal_id=meal.id, name=f"{name}-oats", calories=100))
        db.session.add(UserWater(user_id=u.id, date=date(2026, 6, 1), amount=1.0))
        db.session.add(UserWeight(user_id=u.id, date=date(2026, 6, 1), weight=80))
        session = TrainingSession(user_id=u.id, status="done")
        db.session.add(session)
        db.session.flush()
        db.session.add(SessionExercise(session_id=session.id, exercise_id="bench_press"))
        start = datetime(2026, 6, 1, 22, tzinfo=timezone.utc)
        db.session.add(
            SleepEntry(user_id=u.id, sleep_start=start, sleep_end=start.replace(hour=23), duration_minutes=60, quality_score=50)
        )
        db.session.add(OAuthAccount(provider="google", provider_user_id=f"g-{name}", user_id=u.id))
        db.session.commit()
        return u

    return make("rich"), make("bystander")


def _counts(user_id):
    from backend.app.models.nutrition.meal import Meal
    from backend.app.models.nutrition.meal_item import MealItem
    from backend.app.models.nutrition.user_water import UserWater
    from backend.app.models.nutrition.user_weight import UserWeight
    from backend.app.models.recovery.sleep_entry import SleepEntry
    from backend.app.models.training_session import SessionExercise, TrainingSession

    meal_ids = [m.id for m in Meal.query.filter_by(user_id=user_id)]
    session_ids = [s.id for s in TrainingSession.query.filter_by(user_id=user_id)]
    return {
        "meals": len(meal_ids),
        "meal_items": MealItem.query.filter(MealItem.meal_id.in_(meal_ids)).count() if meal_ids else 0,
        "water": UserWater.query.filter_by(user_id=user_id).count(),
        "weight": UserWeight.query.filter_by(user_id=user_id).count(),
        "sessions": len(session_ids),
        "exercises": SessionExercise.query.filter(SessionExercise.session_id.in_(session_ids)).count() if session_ids else 0,
        "sleep": SleepEntry.query.filter_by(user_id=user_id).count(),
    }


def test_withdrawal_page_explains_and_needs_one_confirmation(client, rich_user):
    me, _ = rich_user
    _login(client, "rich@example.com")

    page = _get(client, "/consent/withdraw").get_data(as_text=True)
    assert "Буде видалено одразу" in page and "Залишиться" in page and "/privacy/my-data" in page

    _post(client, "/consent/withdraw", data={})  # no confirmation: nothing happens
    db.session.expire_all()
    assert has_current_consent(db.session.get(User, me.id))
    assert all(_counts(me.id).values())


def test_withdrawal_erases_consent_based_data_and_keeps_the_account(client, rich_user):
    from backend.app.models.oauth_account import OAuthAccount
    from backend.app.training.models.fatigue_state import FatigueState

    me, other = rich_user
    fatigue_id, my_hash = me.fatigue_state_id, me.password
    _login(client, "rich@example.com")

    response = _post(client, "/consent/withdraw", data={"confirm_erase": "on"})

    assert response.status_code == 302 and response.location.startswith("/consent")
    db.session.expire_all()
    me = db.session.get(User, me.id)
    # Erased: everything the consent covered.
    assert not any(_counts(me.id).values())
    assert me.age is None and me.weight is None and me.fatigue_state_id is None
    assert db.session.get(FatigueState, fatigue_id) is None
    assert me.profile is not None and me.profile.age is None and me.profile.weight is None
    # Kept: the account and its sign-in methods.
    assert me.email == "rich@example.com" and me.password == my_hash
    assert OAuthAccount.query.filter_by(user_id=me.id).count() == 1
    assert me.privacy_accepted_at is not None
    # Processing stops: the gate refuses everything until consent is given again.
    assert not has_current_consent(me)
    assert _get(client, "/api/nutrition/day").get_json()["code"] == "consent_required"
    # Nobody else is touched.
    assert all(_counts(other.id).values())
    assert db.session.get(User, other.id).age == 30


def test_after_withdrawal_the_user_can_consent_again_or_leave(client, rich_user):
    _login(client, "rich@example.com")
    _post(client, "/consent/withdraw", data={"confirm_erase": "on"})

    assert _get(client, "/privacy/my-data").status_code == 200
    assert _get(client, "/profile/").status_code == 200
    _post(client, "/consent", data={**BOTH, "next": "/dashboard/"})
    assert _get(client, "/dashboard/").status_code == 200
    assert _get(client, "/api/nutrition/day").status_code == 200


def test_withdrawal_over_the_api_needs_confirmation(client, rich_user):
    me, _ = rich_user
    assert client.delete("/api/consent", json={"confirm_erase": True}).status_code == 401
    _login(client, "rich@example.com")

    refused = client.delete("/api/consent", json={})
    assert refused.status_code == 400 and refused.get_json()["code"] == "confirm_erase_required"
    db.session.expire_all()
    assert has_current_consent(db.session.get(User, me.id))

    g.pop("_login_user", None)
    done = client.delete("/api/v1/consent", json={"confirm_erase": True})
    assert done.status_code == 200 and done.get_json()["status"] == "withdrawn"
    db.session.expire_all()
    assert not has_current_consent(db.session.get(User, me.id))
    assert not any(_counts(me.id).values())


def test_a_telegram_session_can_withdraw(client, rich_user):
    me, _ = rich_user
    identity = TelegramIdentity(user_id=me.id, telegram_user_id=777)
    db.session.add(identity)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = me.get_id()
        session["_fresh"] = True
        session["tg_identity"] = identity.id

    g.pop("_login_user", None)
    assert client.delete("/api/consent", json={"confirm_erase": True}).status_code == 200

    db.session.expire_all()
    assert TelegramIdentity.query.filter_by(user_id=me.id).count() == 1  # sign-in kept
    assert not any(_counts(me.id).values())


def test_export_includes_own_fatigue_state_only(client, rich_user):
    me, other = rich_user
    _login(client, "rich@example.com")

    tables = _get(client, "/privacy/my-data").get_json()["tables"]

    assert [row["id"] for row in tables["te_fatigue_state"]] == [me.fatigue_state_id]
    assert tables["te_fatigue_state"][0]["sleep"] == 6.5
    assert other.fatigue_state_id not in [row["id"] for row in tables["te_fatigue_state"]]


def test_bot_explains_how_to_get_data_without_a_password(monkeypatch):
    from telegram_bot.handlers import consent as bot_consent

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST-TOKEN-not-real-0000000000000")
    monkeypatch.setenv("TELEGRAM_BOT_API_SECRET", "x" * 40)
    monkeypatch.setenv("NOSI_FIT_BASE_URL", "https://nosifit.example")
    text = bot_consent.mydata_text()

    assert "https://nosifit.example/auth/reset" in text
    assert "https://nosifit.example/privacy/my-data" in text
