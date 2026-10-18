"""Weekly training plan: manual editing, completion, Premium generation.

The builder tests need no database: they feed the real exercise catalog to the
pure planner. The API tests cover ownership, validation, completion history
and the backend Premium check.
"""

import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from api.routes import training as training_routes
from backend.app.extensions import db
from backend.app.models.injury import Injury
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.models.user import User
from backend.app.models.user_injury import UserInjury
from backend.app.services.training import plan_builder, plan_days
from backend.app.services.training.model.context import TrainingContext
from backend.app.services.training.model.records import ExerciseInfo
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.performance_state import PerformanceState
from backend.app.training.models.training_plan import TrainingPlan

WEDNESDAY = dt.date(2026, 10, 14)


# --- the planner (pure) -------------------------------------------------------------


@pytest.fixture(scope="module")
def catalog():
    rows = {}
    for item in load_exercise_catalog():
        info = ExerciseInfo.from_mapping({**item, "id": item["slug"]})
        rows[info.id] = info
    return rows


def build(catalog, owned=(), **context):
    days = context.pop("training_days", None)
    settings = context.pop("day_settings", None)
    return plan_builder.build_week(
        TrainingContext(**context), catalog, training_days=days, day_settings=settings, owned_equipment=owned
    )


def test_only_the_selected_days_are_trained_the_rest_is_rest(catalog):
    week = build(catalog, training_days=["tue", "sat"], goal="hypertrophy", experience="intermediate")

    assert list(week.days) == ["tue", "sat"]
    assert week.rest_days == ["mon", "wed", "thu", "fri", "sun"]
    assert all(day.exercises for day in week.days.values())


def test_without_selected_days_the_weekly_frequency_decides(catalog):
    week = build(catalog, workouts_per_week=4)

    assert list(week.days) == ["mon", "tue", "thu", "fri"]
    assert week.split == "upper_lower"


def test_seven_training_days_leave_no_rest_day_and_are_refused(catalog):
    with pytest.raises(Exception, match="rest day"):
        build(catalog, training_days=list(plan_days.WEEKDAYS))
    with pytest.raises(Exception, match="unknown day"):
        build(catalog, training_days=["mon", "funday"])


def test_the_same_input_gives_the_same_plan(catalog):
    first = build(catalog, workouts_per_week=5, goal="hypertrophy", experience="advanced").to_payload()
    second = build(catalog, workouts_per_week=5, goal="hypertrophy", experience="advanced").to_payload()

    assert first == second


@pytest.mark.parametrize("location, equipment, allowed", [
    ("outdoors", ["bar", "barbell", "dumbbells"], {"bar"}),  # a barbell does not go to the park
    ("home", ["dumbbells", "bench"], {"dumbbells", "bench"}),
    ("home", [], set()),
    ("gym", None, None),
])
def test_exercises_never_need_equipment_the_day_does_not_have(catalog, location, equipment, allowed):
    week = build(
        catalog,
        training_days=["mon", "wed", "fri"],
        day_settings={d: {"location": location, "equipment": equipment} for d in ("mon", "wed", "fri")},
        goal="hypertrophy",
        experience="intermediate",
    )

    for day in week.days.values():
        assert day.location == location
        for item in day.exercises:
            needed = set(item.exercise.equipment) - {"bodyweight"}
            if allowed is not None:
                assert needed <= allowed, (item.exercise.slug, needed)


def test_day_labels_are_the_ones_the_interface_translates(catalog):
    labels = {"push", "pull", "legs", "upper", "lower", "full_body"}

    for days in (1, 2, 3, 4, 5, 6):
        week = build(catalog, workouts_per_week=days)
        assert {day.label for day in week.days.values()} <= labels


def test_a_location_is_not_the_same_as_equipment(catalog):
    owned = ["dumbbells", "bench", "barbell"]
    week = build(
        catalog,
        owned=owned,
        training_days=["mon", "tue", "thu"],
        day_settings={"mon": {"location": "home"}, "tue": {"location": "outdoors"}, "thu": {"location": "gym"}},
        goal="hypertrophy",
        experience="intermediate",
    )

    assert set(week.days["mon"].equipment) == set(owned)  # what is owned is available at home
    assert set(week.days["tue"].equipment) <= plan_days.OUTDOOR_EQUIPMENT  # but not outdoors
    assert week.days["thu"].equipment is None  # a gym is not restricted


@pytest.mark.parametrize("goal", ["maintenance", "general_fitness", "strength", "hypertrophy"])
@pytest.mark.parametrize("experience", ["beginner", "advanced"])
@pytest.mark.parametrize("days", [1, 3, 4, 6])
def test_no_variant_repeats_in_a_day_no_exercise_more_than_twice_and_no_padding(catalog, goal, experience, days):
    week = build(catalog, goal=goal, experience=experience, workouts_per_week=days)
    groups = plan_builder.load_variant_groups()
    used = {}

    for day in week.days.values():
        assert len(day.exercises) <= plan_builder.DAY_EXERCISE_LIMIT[experience]
        seen = [groups[i.exercise.slug] for i in day.exercises if i.exercise.slug in groups]
        assert len(seen) == len(set(seen))  # one deadlift, one curl, one row ... per day
        for item in day.exercises:
            used[item.exercise.slug] = used.get(item.exercise.slug, 0) + 1

    assert max(used.values(), default=0) <= plan_builder.MAX_WEEKLY_REPEATS
    for row in week.coverage.values():
        assert row["planned"] <= row["upper"] * 1.3  # no muscle is overloaded

    assert {n["code"] for n in week.notes if n["code"] == "volume_high"} == (
        {"volume_high"} if any(r["planned"] > r["upper"] for r in week.coverage.values()) else set()
    )


def test_what_cannot_be_covered_is_reported_not_padded(catalog):
    week = build(catalog, available_equipment=frozenset({"bodyweight"}), workouts_per_week=3, goal="hypertrophy",
                 experience="intermediate")

    for day in week.days.values():
        for item in day.exercises:
            assert set(item.exercise.equipment) <= {"bodyweight"}
    notes = {n["code"]: n for n in week.notes}
    assert "lats" in notes["split_skips"]["muscles"] or "lats" in notes["volume_short"]["muscles"]


def test_back_to_back_days_do_not_train_the_same_muscles_when_the_split_allows(catalog):
    week = build(catalog, training_days=["mon", "tue", "thu", "fri"], goal="hypertrophy", experience="intermediate")

    assert week.days["mon"].label != week.days["tue"].label
    assert week.days["thu"].label != week.days["fri"].label
    assert not [n for n in week.notes if n["code"] == "back_to_back"]


def test_full_body_on_consecutive_days_is_flagged(catalog):
    week = build(catalog, training_days=["mon", "tue", "wed"], goal="general_fitness", experience="beginner")

    assert {n["code"] for n in week.notes} >= {"back_to_back"}


def test_the_library_holds_only_known_exercises_and_variant_groups_stay_inside_it(catalog):
    library = plan_builder.load_library()
    slugs = {info.slug for info in catalog.values()}

    assert library <= slugs
    assert set(plan_builder.load_variant_groups()) <= library


# --- the API -------------------------------------------------------------------------


@pytest.fixture
def signed_in(client, user):
    client.post("/auth/login", data={"email": user.email, "password": "password123"})
    return client


@pytest.fixture
def library(app):
    for item in load_exercise_catalog():
        db.session.add(Exercise(**item))
    db.session.commit()
    return {row.slug: row for row in Exercise.query.all()}


@pytest.fixture
def today(monkeypatch):
    monkeypatch.setattr(training_routes, "_local_today", lambda: WEDNESDAY)
    return WEDNESDAY


def entry(exercise, sets=3, reps="8-12"):
    return {"exercise": {"id": exercise.id}, "sets": sets, "reps": reps}


def make_plan(client, exercises, **extra):
    days = {"mon": {"exercises": exercises}, "wed": {"exercises": exercises}, "fri": {"exercises": exercises}}
    response = client.post("/api/training/plans", json={"name": "Week", "is_active": True, "days": days, **extra})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def other_user(email="other@example.com"):
    other = User(username="other", email=email, password=generate_password_hash("password123"))
    db.session.add(other)
    db.session.commit()
    return other


def test_manual_plan_keeps_location_equipment_and_exercise_order(signed_in, library):
    squat, bench = library["barbell-back-squat"], library["bench-press"]
    plan = signed_in.post("/api/training/plans", json={
        "name": "Mine",
        "days": {
            "mon": {"location": "gym", "equipment": ["barbell", "bench"], "exercises": [entry(bench), entry(squat)]},
            "tue": {"exercises": []},
        },
    }).get_json()

    stored = signed_in.get("/api/training/plans").get_json()[0]["days"]
    assert [e["exercise"]["id"] for e in stored["mon"]["exercises"]] == [bench.id, squat.id]
    assert stored["mon"]["location"] == "gym"
    assert stored["mon"]["equipment"] == ["barbell", "bench"]
    assert stored["tue"] == {"exercises": []}
    assert plan["id"] == signed_in.get("/api/training/plans").get_json()[0]["id"]


@pytest.mark.parametrize("day", [
    {"location": "moon", "exercises": []},
    {"location": "gym", "equipment": ["flux-capacitor"], "exercises": []},
    {"equipment": "barbell", "exercises": []},
])
def test_location_and_equipment_are_validated(signed_in, day):
    response = signed_in.post("/api/training/plans", json={"name": "x", "days": {"mon": day}})

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_input"


def test_an_exercise_needing_missing_equipment_is_rejected_for_that_day(signed_in, library):
    response = signed_in.post("/api/training/plans", json={
        "name": "x",
        "days": {"mon": {"location": "outdoors", "equipment": ["bar"], "exercises": [entry(library["bench-press"])]}},
    })

    assert response.status_code == 400
    assert "barbell" in response.get_json()["message"]

    ok = signed_in.post("/api/training/plans", json={
        "name": "x",
        "days": {"mon": {"location": "outdoors", "equipment": ["bar"], "exercises": [entry(library["pull-ups"])]}},
    })
    assert ok.status_code == 200


def test_editing_a_plan_without_days_or_with_some_days_keeps_the_others(signed_in, library):
    plan = make_plan(signed_in, [entry(library["push-ups"])])

    renamed = signed_in.put(f"/api/training/plans/{plan['id']}", json={"name": "Renamed"}).get_json()
    assert set(renamed["days"]) == {"mon", "wed", "fri"}

    changed = signed_in.put(
        f"/api/training/plans/{plan['id']}", json={"days": {"mon": {"exercises": []}}}
    ).get_json()
    assert changed["days"]["mon"]["exercises"] == []
    assert len(changed["days"]["wed"]["exercises"]) == 1
    assert len(changed["days"]["fri"]["exercises"]) == 1


def test_other_users_plans_are_invisible_for_edit_week_and_completion(signed_in, library):
    stranger = other_user()
    foreign = TrainingPlan(user_id=stranger.id, name="Theirs", days={"mon": {"exercises": []}})
    db.session.add(foreign)
    db.session.commit()

    assert signed_in.put(f"/api/training/plans/{foreign.id}", json={"name": "x"}).status_code == 404
    assert signed_in.get(f"/api/training/plans/{foreign.id}/week").status_code == 404
    assert signed_in.post(f"/api/training/plans/{foreign.id}/days/mon/complete").status_code == 404
    assert TrainingSession.query.count() == 0


def test_week_overview_marks_rest_days_and_completion(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["push-ups"])], is_active=True)

    week = signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()
    by_day = {d["key"]: d for d in week["days"]}

    assert week["week_start"] == "2026-10-12"
    assert [d["key"] for d in week["days"]] == list(plan_days.WEEKDAYS)
    assert by_day["tue"]["rest"] is True and by_day["mon"]["rest"] is False
    assert by_day["wed"]["is_today"] is True
    assert not any(d["completed"] for d in week["days"])


def test_completing_a_day_twice_creates_one_session(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["push-ups"]), entry(library["plank"], reps=None)])

    first = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")
    second = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")

    assert first.status_code == second.status_code == 200
    assert first.get_json()["already_completed"] is False
    assert second.get_json()["already_completed"] is True
    assert first.get_json()["session_id"] == second.get_json()["session_id"]
    sessions = TrainingSession.query.all()
    assert len(sessions) == 1
    assert (sessions[0].plan_id, sessions[0].plan_day, sessions[0].plan_date) == (plan["id"], "wed", WEDNESDAY)
    assert sessions[0].status == "finished"
    assert {r.exercise_id for r in sessions[0].exercises} == {library["push-ups"].id, library["plank"].id}
    week = {d["key"]: d for d in signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()["days"]}
    assert week["wed"]["completed"] is True and week["mon"]["completed"] is False


def test_editing_or_deleting_the_plan_keeps_the_completion_history(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["push-ups"])])
    done = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete").get_json()

    signed_in.put(f"/api/training/plans/{plan['id']}", json={"days": {"wed": {"exercises": [entry(library["squat"])]}}})
    session = db.session.get(TrainingSession, done["session_id"])
    assert [r.exercise_id for r in session.exercises] == [library["push-ups"].id]  # what was done stays
    week = {d["key"]: d for d in signed_in.get(f"/api/training/plans/{plan['id']}/week").get_json()["days"]}
    assert week["wed"]["completed"] is True

    again = signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete").get_json()
    assert again["already_completed"] is True and TrainingSession.query.count() == 1

    signed_in.delete(f"/api/training/plans/{plan['id']}")
    db.session.expire_all()
    kept = db.session.get(TrainingSession, done["session_id"])
    assert kept is not None and kept.plan_id is None and kept.plan_date == WEDNESDAY


def test_rest_days_and_future_days_cannot_be_completed_past_days_count_for_their_date(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["push-ups"])])

    rest = signed_in.post(f"/api/training/plans/{plan['id']}/days/tue/complete")
    future = signed_in.post(f"/api/training/plans/{plan['id']}/days/fri/complete")
    past = signed_in.post(f"/api/training/plans/{plan['id']}/days/mon/complete")

    assert (rest.status_code, rest.get_json()["code"]) == (409, "rest_day")
    assert (future.status_code, future.get_json()["code"]) == (409, "day_in_future")
    assert past.status_code == 200 and past.get_json()["date"] == "2026-10-12"
    session = db.session.get(TrainingSession, past.get_json()["session_id"])
    assert session.finished_at.date() == dt.date(2026, 10, 12)  # counts on Monday, not on the day it was ticked
    assert signed_in.post(f"/api/training/plans/{plan['id']}/days/nope/complete").status_code == 404


def test_the_unique_index_stops_a_second_session_for_one_plan_date(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["push-ups"])])
    signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")

    db.session.add(TrainingSession(user_id=plan["user_id"], plan_id=plan["id"], plan_day="wed", plan_date=WEDNESDAY))
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()


# --- Premium generation -----------------------------------------------------------------


def test_generation_is_refused_without_premium_on_the_backend(signed_in, library):
    before = TrainingPlan.query.count()

    response = signed_in.post("/api/training/plans/generate", json={"training_days": ["mon", "wed"]})

    assert response.status_code == 403
    assert response.get_json()["code"] == "premium_required"
    assert TrainingPlan.query.count() == before


def test_generation_needs_a_signed_in_user(client, library):
    response = client.post("/api/training/plans/generate", json={})

    assert response.status_code == 401


def test_manual_plans_work_without_premium(signed_in, library):
    assert make_plan(signed_in, [entry(library["push-ups"])])["id"]


@pytest.fixture
def premium(user):
    user.is_premium = True
    db.session.commit()


def test_premium_generation_returns_an_editable_unsaved_draft(signed_in, library, premium):
    response = signed_in.post("/api/training/plans/generate", json={
        "training_days": ["tue", "thu", "sat"],
        "days": {"tue": {"location": "gym"}, "thu": {"location": "home", "equipment": ["dumbbells", "bench"]},
                 "sat": {"location": "outdoors", "equipment": ["bar", "barbell"]}},
    })

    assert response.status_code == 200
    draft = response.get_json()
    assert TrainingPlan.query.count() == 0  # a draft: nothing is saved until the user saves it
    assert set(draft["days"]) == {"tue", "thu", "sat"}
    assert draft["rest_days"] == ["mon", "wed", "fri", "sun"]
    assert draft["days"]["thu"]["equipment"] == ["bench", "dumbbells"]
    assert draft["days"]["sat"]["equipment"] == ["bar"]  # the barbell is not for the park
    assert draft["explanation"]["tue"]["label"] and draft["injuries_considered"] is False
    for key in ("thu", "sat"):
        allowed = set(draft["days"][key]["equipment"]) | {"bodyweight"}
        for item in draft["days"][key]["exercises"]:
            assert set(Exercise.query.get(item["exercise"]["id"]).equipment) <= allowed

    saved = signed_in.post("/api/training/plans", json={"name": "Generated", "days": draft["days"]})
    assert saved.status_code == 200  # the draft is accepted as it is, and can be edited first
    assert saved.get_json()["days"]["sat"]["equipment"] == ["bar"]


def test_generation_rejects_bad_input_and_says_when_injuries_are_not_considered(signed_in, library, premium, user):
    assert signed_in.post("/api/training/plans/generate", json={"training_days": ["mon", "xyz"]}).status_code == 400
    assert signed_in.post("/api/training/plans/generate", json={"training_days": list(plan_days.WEEKDAYS)}).status_code == 400
    assert signed_in.post("/api/training/plans/generate", json={"days": {"mon": "gym"}}).status_code == 400

    knee = Injury(name="Knee")
    db.session.add(knee)
    db.session.commit()
    db.session.add(UserInjury(user_id=user.id, injury_id=knee.id))
    db.session.commit()

    notes = signed_in.post("/api/training/plans/generate", json={}).get_json()["notes"]
    assert {"code": "injuries_not_considered"} in notes


def test_a_user_with_no_equipment_and_no_gym_gets_bodyweight_exercises_only(signed_in, library, premium):
    draft = signed_in.post("/api/training/plans/generate", json={"training_days": ["mon", "thu"]}).get_json()

    for day in draft["days"].values():
        for item in day["exercises"]:
            assert set(Exercise.query.get(item["exercise"]["id"]).equipment) <= {"bodyweight"}


def test_completed_session_feeds_the_training_model(signed_in, library, today):
    plan = make_plan(signed_in, [entry(library["bench-press"], sets=4, reps="8")])
    signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")
    signed_in.post(f"/api/training/plans/{plan['id']}/days/wed/complete")

    session = TrainingSession.query.one()
    # The cumulative load holds this session once, however often it was requested.
    assert PerformanceState.query.one().training_load == pytest.approx(session.internal_load)
    row = SessionExercise.query.filter_by(session_id=session.id).one()
    assert (row.sets_done, row.reps_done) == (4, "8")
    assert session.muscle_loads  # the model sees the workout like any logged session
