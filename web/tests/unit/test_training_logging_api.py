"""Workout logging API used by the Telegram bot: exercise search, recent
exercises, today's session and edits through /sessions/complete."""

import datetime as dt

import pytest

from backend.app.extensions import db
from backend.app.models.training_session import SessionExercise, TrainingSession
from backend.app.services.training.exercise_search import normalize, search_exercises
from backend.app.training.exercises.catalog import load_exercise_catalog
from backend.app.training.models.exercise import Exercise
from backend.app.training.models.performance_state import PerformanceState


def login(client):
    return client.post("/auth/login", data={"email": "test@example.com", "password": "password123"})


@pytest.fixture
def catalog(app):
    rows = {}
    for item in load_exercise_catalog():
        exercise = Exercise(**item)
        db.session.add(exercise)
        rows[item["slug"]] = exercise
    db.session.commit()
    return rows


def past_session(user, catalog, days_ago, items):
    finished = dt.datetime.utcnow() - dt.timedelta(days=days_ago)
    session = TrainingSession(
        user_id=user.id, status="finished", started_at=finished - dt.timedelta(hours=1), finished_at=finished
    )
    db.session.add(session)
    db.session.flush()
    for slug, values in items:
        db.session.add(SessionExercise(session_id=session.id, exercise_id=catalog[slug].id, **values))
    db.session.commit()
    return session


def search(client, q, **params):
    response = client.get("/api/training/exercises/search", query_string={"q": q, **params})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def slugs(payload):
    return [item["slug"] for item in payload["items"]]


def save(client, items, session_id=None):
    payload = {"exercises": items}
    if session_id is not None:
        payload["session_id"] = session_id
    response = client.post("/api/training/sessions/complete", json=payload)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def today(client):
    response = client.get("/api/training/sessions/today")
    assert response.status_code == 200
    return response.get_json()["session"]


def item(catalog, slug, **values):
    return {"exercise": {"id": catalog[slug].id}, **values}


# --- search -------------------------------------------------------------------------


def test_exact_ukrainian_name_comes_first(client, user, catalog):
    login(client)
    result = search(client, "Жим штанги лежачи")
    assert slugs(result)[0] == "bench-press"
    first = result["items"][0]
    assert first["name"] == "Жим штанги лежачи"
    assert first["measurement_type"] == "reps"
    assert first["accepts_load"] is True
    assert first["last"] is None


def test_partial_query_prefers_words_that_start_with_it(client, user, catalog):
    login(client)
    result = search(client, "жим", limit=20)
    found = slugs(result)
    assert result["items"][0]["name"].casefold().startswith("жим")
    assert "bench-press" in found
    # "Віджимання" contains "жим" inside a word, so it ranks below every press.
    if "push-ups" in found:
        assert found.index("push-ups") > found.index("bench-press")


def test_several_word_prefixes(client, user, catalog):
    login(client)
    assert slugs(search(client, "тяга верх"))[0] == "lat-pulldown"


@pytest.mark.parametrize(
    "query, expected",
    [("присидання", "squat"), ("підтягуваня", "pull-ups"), ("жм лежачи", "bench-press")],
)
def test_typos_still_find_the_exercise(client, user, catalog, query, expected):
    login(client)
    found = slugs(search(client, query, limit=20))
    assert found
    assert any(expected in slug for slug in found)


def test_english_name_and_slug(client, user, catalog):
    login(client)
    assert "bench-press" in slugs(search(client, "barbell bench"))
    assert slugs(search(client, "bench-press"))[0] == "bench-press"


def test_no_results_and_empty_query(client, user, catalog):
    login(client)
    assert search(client, "xyzqqq") == {"items": [], "query": "xyzqqq", "has_more": False}
    assert search(client, "  ")["items"] == []


def test_paging_reports_more_results(client, user, catalog):
    login(client)
    first = search(client, "жим", limit=3)
    second = search(client, "жим", limit=3, offset=3)
    assert first["has_more"] is True
    assert not set(slugs(first)) & set(slugs(second))


def test_exercises_done_before_rank_first_and_carry_last_values(client, user, catalog):
    past_session(user, catalog, 2, [("dumbbell-bench-press", {"sets_done": 3, "reps_done": "10", "load_done": 24, "rpe": 8})])
    login(client)
    result = search(client, "жим")
    assert slugs(result)[0] == "dumbbell-bench-press"
    assert result["items"][0]["last"] == {
        "sets": 3, "reps": "10", "reps_count": 10, "duration_sec": None, "load": 24.0, "rir": 2, "rpe": 8.0,
        # logged before sets were stored: three equal sets
        "set_entries": [{"reps": 10, "load": 24.0}] * 3,
    }


def test_search_uses_the_requested_locale(client, user, catalog):
    login(client)
    assert search(client, "bench press", locale="en")["items"][0]["name"] == "Barbell Bench Press"
    assert search(client, "bench press", locale="xx")["items"][0]["name"] == "Жим штанги лежачи"


def test_ranking_is_pure_and_normalised():
    class E:
        def __init__(self, slug, name):
            self.id, self.slug, self.name = slug, slug, name

    rows = [E("a", "Push-Up"), E("b", "Bench Press")]
    names = {"a": "Віджимання", "b": "Жим штанги лежачи"}
    assert [e.slug for e in search_exercises(rows, names, "ЖИМ")] == ["b", "a"]
    assert normalize("  Жим’  штанги-лежачи ") == "жим' штанги лежачи"


def test_search_requires_login(client, catalog):
    assert client.get("/api/training/exercises/search?q=жим").status_code in (302, 401)


# --- recent -------------------------------------------------------------------------


def test_recent_exercises_newest_first_without_today(client, user, catalog):
    past_session(user, catalog, 5, [("plank", {"sets_done": 3, "duration_sec_done": 60})])
    past_session(
        user,
        catalog,
        1,
        [
            ("bench-press", {"sets_done": 3, "reps_done": "8", "load_done": 60, "rpe": 9}),
            ("plank", {"sets_done": 2, "duration_sec_done": 45}),
        ],
    )
    login(client)
    save(client, [item(catalog, "lat-pulldown", sets=3, reps=10, load=50)])

    response = client.get("/api/training/exercises/recent")
    assert response.status_code == 200
    items = response.get_json()["items"]
    # Same session: the exercise logged later counts as more recent.
    assert [i["slug"] for i in items] == ["plank", "bench-press"]
    plank = next(i for i in items if i["slug"] == "plank")
    assert plank["last"]["duration_sec"] == 45 and plank["last"]["reps"] is None
    bench = next(i for i in items if i["slug"] == "bench-press")
    assert bench["last"]["rir"] == 1 and bench["name"] == "Жим штанги лежачи"


def test_recent_is_empty_for_a_new_user(client, user, catalog):
    login(client)
    assert client.get("/api/training/exercises/recent").get_json() == {"items": []}


# --- today's session through /sessions/complete ---------------------------------------


def test_today_is_empty_before_training(client, user, catalog):
    login(client)
    assert today(client) is None


def test_logging_a_workout_step_by_step_keeps_one_session(client, user, catalog):
    login(client)
    bench = item(catalog, "bench-press", sets=1, reps=10, load=60, rir=2)
    first = save(client, [bench])
    session_id = first["id"]

    # more sets, a second exercise, an edited set, a removed set
    for sets in (2, 3):
        save(client, [{**bench, "sets": sets}], session_id)
    pull = item(catalog, "lat-pulldown", sets=1, reps=12, load=45)
    save(client, [{**bench, "sets": 3}, pull], session_id)
    save(client, [{**bench, "sets": 3, "reps": 9, "load": 62.5, "rir": 1}, {**pull, "sets": 2}], session_id)
    save(client, [{**bench, "sets": 2, "reps": 9, "load": 62.5, "rir": 1}, {**pull, "sets": 2}], session_id)

    assert TrainingSession.query.filter_by(user_id=user.id).count() == 1
    current = today(client)
    assert current["id"] == session_id
    assert current["status"] == "finished"
    assert [e["slug"] for e in current["exercises"]] == ["bench-press", "lat-pulldown"]
    bench_row = current["exercises"][0]
    assert (bench_row["sets"], bench_row["reps"], bench_row["reps_count"]) == (2, "9", 9)
    assert (bench_row["load"], bench_row["rir"]) == (62.5, 1)
    assert current["totals"] == {"exercises": 2, "sets": 4}


def test_rir_is_stored_as_rpe(client, user, catalog):
    login(client)
    save(client, [item(catalog, "bench-press", sets=3, reps=8, load=80, rir=3)])
    row = SessionExercise.query.one()
    assert row.rpe == 7.0


@pytest.mark.parametrize("rir", [-1, 10, "a lot", True])
def test_invalid_rir_is_rejected(client, user, catalog, rir):
    login(client)
    response = client.post(
        "/api/training/sessions/complete",
        json={"exercises": [item(catalog, "bench-press", sets=3, reps=8, rir=rir)]},
    )
    assert response.status_code == 400
    assert TrainingSession.query.count() == 0


def test_unknown_exercise_is_rejected(client, user, catalog):
    login(client)
    response = client.post(
        "/api/training/sessions/complete",
        json={"exercises": [{"exercise": {"id": "no-such-exercise"}, "sets": 1}]},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_input"


def test_duration_exercise_logs_seconds(client, user, catalog):
    login(client)
    save(client, [item(catalog, "plank", sets=3, duration_sec=45)])
    plank = today(client)["exercises"][0]
    assert plank["measurement_type"] == "duration"
    assert plank["duration_sec"] == 45 and plank["reps"] is None
    assert plank["accepts_load"] is False


def test_repeated_identical_save_changes_nothing(client, user, catalog):
    login(client)
    items = [item(catalog, "bench-press", sets=3, reps=10, load=60)]
    first = save(client, items)
    for _ in range(3):
        again = save(client, items, first["id"])
        assert again["id"] == first["id"]
        assert again["hard_sets"] == first["hard_sets"]

    session = TrainingSession.query.filter_by(user_id=user.id).one()
    assert len(session.exercises) == 1
    performance = PerformanceState.query.filter_by(user_id=user.id).one()
    assert performance.training_load == pytest.approx(session.internal_load)


def test_deleting_one_exercise(client, user, catalog):
    login(client)
    bench = item(catalog, "bench-press", sets=3, reps=10, load=60)
    plank = item(catalog, "plank", sets=2, duration_sec=60)
    first = save(client, [bench, plank])
    save(client, [plank], first["id"])
    assert [e["slug"] for e in today(client)["exercises"]] == ["plank"]


def test_deleting_the_last_exercise_removes_the_session(client, user, catalog):
    login(client)
    first = save(client, [item(catalog, "bench-press", sets=3, reps=10, load=60)])
    assert PerformanceState.query.filter_by(user_id=user.id).one().training_load > 0

    result = save(client, [], first["id"])

    assert result["id"] is None and result["deleted"] is True
    assert TrainingSession.query.count() == 0
    assert SessionExercise.query.count() == 0
    assert today(client) is None
    assert PerformanceState.query.filter_by(user_id=user.id).one().training_load == pytest.approx(0)


def test_empty_save_never_creates_a_session(client, user, catalog):
    login(client)
    result = save(client, [])
    assert result["id"] is None and result["deleted"] is False
    assert TrainingSession.query.count() == 0


def test_empty_save_cannot_delete_older_or_foreign_sessions(client, user, catalog):
    old = past_session(user, catalog, 3, [("plank", {"sets_done": 2, "duration_sec_done": 60})])
    login(client)
    assert save(client, [], old.id)["deleted"] is False
    assert db.session.get(TrainingSession, old.id) is not None


def test_completing_again_keeps_the_same_finished_session(client, user, catalog):
    login(client)
    items = [item(catalog, "bench-press", sets=3, reps=10, load=60)]
    first = save(client, items)
    again = save(client, items, first["id"])
    assert again["id"] == first["id"]
    assert TrainingSession.query.filter_by(user_id=user.id, status="finished").count() == 1


def test_lost_session_id_is_recovered_from_today(client, user, catalog):
    """A bot restart forgets the id; today's session gives it back."""
    login(client)
    first = save(client, [item(catalog, "bench-press", sets=1, reps=10, load=60)])
    recovered = today(client)["id"]
    save(client, [item(catalog, "bench-press", sets=2, reps=10, load=60)], recovered)
    assert recovered == first["id"]
    assert TrainingSession.query.count() == 1


def test_today_ignores_yesterday(client, user, catalog):
    past_session(user, catalog, 1, [("plank", {"sets_done": 2, "duration_sec_done": 60})])
    login(client)
    assert today(client) is None


def test_strict_save_with_a_stale_session_id_is_rejected(client, user, catalog):
    old = past_session(user, catalog, 1, [("plank", {"sets_done": 2, "duration_sec_done": 60})])
    login(client)
    payload = {"session_id": old.id, "strict": True, "exercises": [item(catalog, "bench-press", sets=1, reps=5)]}

    response = client.post("/api/training/sessions/complete", json=payload)

    assert response.status_code == 404
    assert response.get_json() == {"error": "session_not_found"}
    assert TrainingSession.query.count() == 1
    # Without strict (the web page) the old behaviour stays: a new session.
    del payload["strict"]
    assert client.post("/api/training/sessions/complete", json=payload).status_code == 200
    assert TrainingSession.query.count() == 2


def test_strict_first_save_creates_the_session(client, user, catalog):
    login(client)
    response = client.post(
        "/api/training/sessions/complete",
        json={"session_id": None, "strict": True, "exercises": [item(catalog, "bench-press", sets=1, reps=5)]},
    )
    assert response.status_code == 200
    assert today(client)["id"] == response.get_json()["id"]


# --- sets with their own reps and kg -----------------------------------------------


def test_each_set_keeps_its_reps_and_kg(client, user, catalog):
    login(client)
    sets = [{"reps": 12, "load": 60}, {"reps": 11, "load": 55}, {"reps": 8, "load": 50}]
    save(client, [{"exercise": {"id": catalog["bench-press"].id}, "set_entries": sets}])

    row = SessionExercise.query.one()
    assert row.set_entries == [{"reps": 12, "load": 60.0}, {"reps": 11, "load": 55.0}, {"reps": 8, "load": 50.0}]
    # what the training model reads: 3 sets, mean reps, kg weighted by reps
    assert (row.sets_done, row.reps_done) == (3, "10")
    assert row.load_done == pytest.approx((12 * 60 + 11 * 55 + 8 * 50) / 31, abs=0.01)

    logged = today(client)["exercises"][0]
    assert logged["set_entries"] == row.set_entries
    assert today(client)["totals"]["sets"] == 3


def test_duration_sets(client, user, catalog):
    login(client)
    save(client, [{"exercise": {"id": catalog["plank"].id}, "set_entries": [{"duration_sec": 60, "load": 0}, {"duration_sec": 40, "load": 0}]}])
    row = SessionExercise.query.one()
    assert (row.sets_done, row.duration_sec_done, row.reps_done) == (2, 50, None)


@pytest.mark.parametrize(
    "sets",
    [[], [{"reps": 0, "load": 10}], [{"load": 10}], [{"reps": 5, "duration_sec": 5, "load": 0}], [{"reps": 5, "load": -1}], "3x10"],
)
def test_invalid_sets_are_rejected(client, user, catalog, sets):
    login(client)
    response = client.post(
        "/api/training/sessions/complete",
        json={"exercises": [{"exercise": {"id": catalog["bench-press"].id}, "set_entries": sets}]},
    )
    assert response.status_code == 400
    assert TrainingSession.query.count() == 0


def test_saving_without_sets_drops_stale_sets(client, user, catalog):
    login(client)
    first = save(client, [{"exercise": {"id": catalog["bench-press"].id}, "set_entries": [{"reps": 12, "load": 60}]}])
    save(client, [item(catalog, "bench-press", sets=4, reps=6, load=80)], first["id"])
    row = SessionExercise.query.one()
    assert row.set_entries is None
    assert today(client)["exercises"][0]["set_entries"] == [{"reps": 6, "load": 80.0}] * 4
