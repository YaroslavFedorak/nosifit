from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from backend.app.extensions import db
from backend.app.training.models.exercise import Exercise
from backend.app.training.exercises.prescription import (
    build_entry,
    is_duration_exercise,
    is_per_side,
    measurement_type_of,
    serialize_entry,
)
from backend.app.training.models.muscle import Muscle
from backend.app.training.models.equipment import TEEquipment
from backend.app.training.models.user_pref import UserPreference
from backend.app.services.training.session_service import TrainingSessionService
from backend.app.services.training.model import TrainingModelService
from backend.app.training.training_analysis.recommendations_engine import (
    build_recommendations,
)
from backend.app.models.training_session import TrainingSession
from backend.app.training.models.training_plan import TrainingPlan
from backend.app.training.models.performance_state import PerformanceState
import datetime as dt
from zoneinfo import ZoneInfo

from werkzeug.exceptions import BadRequest, HTTPException

from backend.app.utils.validation import ValidationError, as_db_id, bounded_number
from backend.app.services.training.validation import (
    clean_exercise_id as _clean_exercise_id,
    clean_fatigue as _clean_fatigue,
    clean_reps as _clean_reps,
    clean_set_data as _clean_set_data,
)

APP_TIMEZONE = ZoneInfo("Europe/Warsaw")


def _local_now():
    return dt.datetime.now(APP_TIMEZONE)


def _local_today():
    return _local_now().date()


def _local_date(moment):
    """Local calendar date of a naive UTC datetime."""
    return moment.replace(tzinfo=dt.timezone.utc).astimezone(APP_TIMEZONE).date()


training_api_bp = Blueprint("training_api", __name__, url_prefix="/api/training")


def _error(e):
    if isinstance(e, HTTPException):  # 404 from first_or_404, 400 from bad JSON
        raise e
    if isinstance(e, ValidationError):
        return jsonify({"error": "invalid_input", "message": str(e)}), 400
    current_app.logger.exception("API error")
    # Exception text can contain SQL and internals; it stays in the log.
    return jsonify({"error": "internal_server_error"}), 500


MAX_PLANS_PER_USER = 50
MAX_PLAN_NAME_LENGTH = 100
MAX_EXERCISES_PER_DAY = 40
PLAN_DAY_KEYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
def _clean_plan_name(value, default):
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("name must be text")
    return value.strip()[:MAX_PLAN_NAME_LENGTH]


def _json_body():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise BadRequest("JSON object expected")
    return data


def _active_plan(user):
    plan = (
        TrainingPlan.query.filter_by(user_id=user.id, is_active=True)
        .order_by(TrainingPlan.id.desc())
        .first()
    )
    return plan


def _today_key():
    return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][_local_today().weekday()]


def _plan_entry(exercise, item):
    return build_entry(
        exercise,
        sets=item.get("sets"),
        reps=item.get("reps"),
        duration_sec=item.get("duration_sec"),
        load=item.get("load"),
    )


def _session_entry(exercise, session_exercise):
    entry = build_entry(
        exercise,
        reps=session_exercise.reps_done or session_exercise.reps_planned,
        duration_sec=(
            session_exercise.duration_sec_done
            or session_exercise.duration_sec_planned
        ),
        load=session_exercise.load_done or session_exercise.load_planned,
    )
    entry["sets"] = session_exercise.sets_done or session_exercise.sets_planned or 0
    return entry


def _plan_days_struct(raw):
    if not isinstance(raw, dict):
        raise ValidationError("days must be an object")

    result = {}
    for key, items in raw.items():
        if key not in PLAN_DAY_KEYS:
            raise ValidationError("unknown day")

        if isinstance(items, dict) and "exercises" in items:
            items = items["exercises"]

        if not isinstance(items, list) or len(items) > MAX_EXERCISES_PER_DAY:
            raise ValidationError("too many exercises in a day")

        day_ex = []
        for ex in items:
            exercise = ex.get("exercise") if isinstance(ex, dict) else None
            exercise_id = exercise.get("id") if isinstance(exercise, dict) else None
            if isinstance(exercise_id, bool) or not isinstance(exercise_id, (str, int)):
                continue
            obj = Exercise.query.get(exercise_id)
            if not obj:
                continue

            day_ex.append(
                serialize_entry(
                    obj,
                    _plan_entry(
                        obj,
                        {
                            "sets": bounded_number(
                                ex.get("sets"), 1, 20, integer=True
                            ),
                            "reps": _clean_reps(ex.get("reps")),
                            "duration_sec": bounded_number(
                                ex.get("duration_sec"), 1, 3600, integer=True
                            ),
                            "load": bounded_number(ex.get("load"), 0, 2000),
                        },
                    ),
                )
            )

        result[key] = {"exercises": day_ex}

    return result


@training_api_bp.route("/muscles")
@login_required
def muscles():
    try:
        return jsonify([m.to_dict() for m in Muscle.query.order_by(Muscle.name)])
    except Exception as e:
        return _error(e)


@training_api_bp.route("/equipment")
@login_required
def equipment():
    try:
        return jsonify(
            [e.to_dict() for e in TEEquipment.query.order_by(TEEquipment.name)]
        )
    except Exception as e:
        return _error(e)


@training_api_bp.route("/exercises")
@login_required
def exercises():
    try:
        q = Exercise.query
        muscle = request.args.get("muscle")
        equipment = request.args.get("equipment")
        qstr = request.args.get("q")
        page = max(1, request.args.get("page", 1, type=int) or 1)
        per_page = min(max(1, request.args.get("per_page", 50, type=int) or 50), 100)

        if muscle:
            q = q.filter(
                Exercise.muscles_primary.contains([muscle])
                | Exercise.muscles_secondary.contains([muscle])
            )

        if equipment:
            q = q.filter(Exercise.equipment.contains([equipment]))

        if qstr:
            q = q.filter(Exercise.name.ilike(f"%{qstr}%"))

        items = q.order_by(Exercise.name).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "items": [ex.to_dict() for ex in items.items],
                "page": page,
                "per_page": per_page,
                "total": items.total,
            }
        )
    except Exception as e:
        return _error(e)


@training_api_bp.route("/today")
@login_required
def today():
    try:
        active = (
            TrainingSession.query.filter_by(user_id=current_user.id, status="active")
            .order_by(TrainingSession.started_at.desc())
            .first()
        )

        prefs = {
            p.key: p.value
            for p in UserPreference.query.filter_by(user_id=current_user.id)
        }
        avoid = [
            k.split("injury_")[1]
            for k, v in prefs.items()
            if k.startswith("injury_") and v == "true"
        ]
        no_eq = [
            s.strip().lower()
            for s in (prefs.get("no_equipment") or "").split(",")
            if s.strip()
        ]

        payload = {
            "sessionId": None,
            "title": None,
            "exercises": [],
            "muscles": {},
            "plan": [],
        }
        exercises_raw = []

        if active:
            payload["sessionId"] = str(active.id)
            payload["title"] = "Активна сесія"
            for se in active.exercises:
                ex_obj = Exercise.query.get(se.exercise_id)
                if not ex_obj:
                    continue
                exercises_raw.append(
                    {
                        "exercise": ex_obj,
                        "entry": _session_entry(ex_obj, se),
                    }
                )
        else:
            plan = _active_plan(current_user)
            if not plan or not plan.days:
                return jsonify(payload)

            day = plan.days.get(_today_key()) or next(iter(plan.days.values()))
            for ex in day["exercises"]:
                ex_obj = Exercise.query.get(ex["exercise"]["id"])
                if not ex_obj:
                    continue
                exercises_raw.append(
                    {
                        "exercise": ex_obj,
                        "entry": _plan_entry(ex_obj, ex),
                    }
                )
            payload["title"] = "Рекомендована сесія"
            payload["plan"] = [{"id": plan.id, "name": plan.name}]

        filtered = []
        for item in exercises_raw:
            ex = item["exercise"]
            muscles_all = (ex.muscles_primary or []) + (ex.muscles_secondary or [])
            if any(m.lower() in avoid for m in muscles_all):
                continue
            eq_list = ex.equipment or []
            if no_eq and any(e.lower() in no_eq for e in eq_list):
                continue
            filtered.append(item)

        muscles = {}
        for item in filtered:
            ex = item["exercise"]
            muscles_all = (ex.muscles_primary or []) + (ex.muscles_secondary or [])
            per = 100 / len(muscles_all) if muscles_all else 0
            for m in muscles_all:
                muscles[m] = muscles.get(m, 0) + per

        total = sum(muscles.values()) or 1
        payload["muscles"] = {k: round(v / total, 3) for k, v in muscles.items()}
        payload["exercises"] = [
            serialize_entry(item["exercise"], item["entry"]) for item in filtered
        ]

        return jsonify(payload)
    except Exception as e:
        return _error(e)


@training_api_bp.route("/today-session")
@login_required
def today_session():
    try:
        active = (
            TrainingSession.query.filter_by(user_id=current_user.id, status="active")
            .order_by(TrainingSession.started_at.desc())
            .first()
        )

        result = {"exercises": []}

        if active:
            for se in active.exercises:
                ex = Exercise.query.get(se.exercise_id)
                if not ex:
                    continue
                result["exercises"].append(
                    serialize_entry(ex, _session_entry(ex, se))
                )
            return jsonify(result)

        plan = _active_plan(current_user)
        if not plan:
            return jsonify({"exercises": []})

        day = plan.days.get(_today_key()) or next(iter(plan.days.values()))

        for item in day["exercises"]:
            ex = Exercise.query.get(item["exercise"]["id"])
            if not ex:
                continue
            result["exercises"].append(serialize_entry(ex, _plan_entry(ex, item)))

        return jsonify(result)
    except Exception as e:
        return _error(e)


@training_api_bp.route("/heatmap")
@login_required
def heatmap():
    try:
        year = int(request.args.get("year", dt.date.today().year))
        start = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)

        local_start = dt.datetime.combine(start, dt.time.min, tzinfo=APP_TIMEZONE)

        local_end = dt.datetime.combine(end, dt.time.max, tzinfo=APP_TIMEZONE)

        utc_start = local_start.astimezone(dt.timezone.utc).replace(tzinfo=None)

        utc_end = local_end.astimezone(dt.timezone.utc).replace(tzinfo=None)

        today = _local_today()
        calendar = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
        stress = TrainingModelService.stress_days(
            current_user.id,
            [d for d in calendar if d <= today],
            _local_date,
            utc_start,
            utc_end,
        )

        days = []
        for d in calendar:
            item = stress.get(d) or {}
            days.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "hard_sets": item.get("hard_sets", 0.0),
                    "session_training_stress_proxy": item.get(
                        "session_training_stress_proxy", 0.0
                    ),
                    "intensity_percent": item.get("intensity_percent", 0),
                    "is_today": d == today,
                }
            )

        return jsonify({"days": days})
    except Exception as e:
        return _error(e)


@training_api_bp.route("/plans", methods=["GET"])
@login_required
def plans():
    try:
        return jsonify(
            [p.to_dict() for p in TrainingPlan.query.filter_by(user_id=current_user.id)]
        )
    except Exception as e:
        return _error(e)


@training_api_bp.route("/plans", methods=["POST"])
@login_required
def create_plan():
    try:
        data = _json_body()

        if TrainingPlan.query.filter_by(user_id=current_user.id).count() >= MAX_PLANS_PER_USER:
            return jsonify({"error": "too_many_plans"}), 400

        plan = TrainingPlan(
            user_id=current_user.id,
            name=_clean_plan_name(data.get("name"), "Plan"),
            is_active=data.get("is_active") is True,
            days=_plan_days_struct(data.get("days", {})),
        )

        if plan.is_active:
            TrainingPlan.query.filter_by(
                user_id=current_user.id, is_active=True
            ).update({"is_active": False})

        db.session.add(plan)
        db.session.commit()
        return jsonify(plan.to_dict())
    except Exception as e:
        return _error(e)


@training_api_bp.route("/plans/<int:plan_id>", methods=["PUT"])
@login_required
def update_plan(plan_id):
    try:
        plan = TrainingPlan.query.filter_by(
            id=plan_id, user_id=current_user.id
        ).first_or_404()
        data = _json_body()

        plan.name = _clean_plan_name(data.get("name"), plan.name)
        plan.days = _plan_days_struct(data.get("days", {}))

        if data.get("is_active", plan.is_active) is True:
            TrainingPlan.query.filter_by(
                user_id=current_user.id, is_active=True
            ).update({"is_active": False})
            plan.is_active = True
        else:
            plan.is_active = False

        db.session.commit()
        return jsonify(plan.to_dict())
    except Exception as e:
        return _error(e)


@training_api_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
@login_required
def delete_plan(plan_id):
    try:
        plan = TrainingPlan.query.filter_by(
            id=plan_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(plan)
        db.session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return _error(e)


def _saved_workout_today(session_id):
    """The user's session saved earlier today from the workout page, if any.

    Only today's sessions can be re-saved this way; anything else (another
    user's id, an older day, garbage) falls back to creating a new session.
    """
    session_id = as_db_id(session_id)
    if session_id is None:
        return None
    session = TrainingSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if session is None or session.started_at is None:
        return None
    if _local_date(session.started_at) != _local_today():
        return None
    return session


def _completed_session_payload(session):
    summary = TrainingModelService.session_summary(session)
    return {
        "id": session.id,
        "rpe_avg": session.rpe_avg,
        # Legacy multiplier-based value; kept until its consumers move.
        "internal_load": session.internal_load,
        "hard_sets": summary["hard_sets"],
        "session_training_stress_proxy": summary["session_training_stress_proxy"],
        "volume_load_kg": summary["volume_load_kg"],
        "muscle_sets": summary["muscle_sets"],
    }


@training_api_bp.route("/sessions/complete", methods=["POST"])
@login_required
def complete_session():
    try:
        data = _json_body()
        fatigue_before = _clean_fatigue(data.get("fatigue_before"))
        fatigue_after = _clean_fatigue(data.get("fatigue_after"))

        raw = data.get("exercises", [])
        if isinstance(raw, dict):
            raw = [item for values in raw.values() if isinstance(values, list) for item in values]
        if not isinstance(raw, list) or len(raw) > 100:
            raise ValidationError("exercises must be a list of at most 100 items")

        exercises = []
        for item in raw:
            exercise_data = item.get("exercise") if isinstance(item, dict) else None
            exercise_id = exercise_data.get("id") if isinstance(exercise_data, dict) else None
            if not exercise_id:
                continue
            exercises.append(
                (
                    _clean_exercise_id(exercise_id),
                    _clean_set_data(
                        {
                            "sets_done": item.get("sets"),
                            "reps_done": item.get("reps"),
                            "duration_sec_done": item.get("duration_sec"),
                            "load_done": item.get("load"),
                            "rpe": item.get("rpe"),
                        }
                    ),
                )
            )

        saved = _saved_workout_today(data.get("session_id"))
        if saved is not None:
            session = TrainingSessionService.replace_exercises(
                saved, exercises, fatigue_after
            )
            return jsonify(_completed_session_payload(session))

        existing = (
            TrainingSession.query.filter_by(
                user_id=current_user.id,
                status="active",
            )
            .order_by(TrainingSession.started_at.desc())
            .first()
        )

        if existing:
            TrainingSessionService.finish_session(
                existing,
                fatigue_after,
            )

        session = TrainingSessionService.start_session(
            current_user,
            fatigue_before=fatigue_before,
        )

        for exercise_id, set_data in exercises:
            TrainingSessionService.update_exercise(
                session,
                exercise_id,
                set_data,
            )

        TrainingSessionService.finish_session(
            session,
            fatigue_after,
        )

        return jsonify(_completed_session_payload(session))

    except Exception as e:
        return _error(e)


@training_api_bp.route(
    "/sessions/<int:session_id>/exercise/<exercise_id>", methods=["POST"]
)
@login_required
def update_session_exercise(session_id, exercise_id):
    try:
        data = _clean_set_data(_json_body())
        exercise_id = _clean_exercise_id(exercise_id)

        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id,
            status="active",
        ).first_or_404()

        se = TrainingSessionService.update_exercise(session, exercise_id, data)

        return jsonify(
            {
                "status": "ok",
                "exercise_id": exercise_id,
                "sets_done": se.sets_done,
                "reps_done": se.reps_done,
                "duration_sec_done": se.duration_sec_done,
                "load_done": se.load_done,
                "rpe": se.rpe,
            }
        )
    except Exception as e:
        return _error(e)


@training_api_bp.route("/sessions/start", methods=["POST"])
@login_required
def start_session():
    try:
        data = _json_body()
        fatigue_before = _clean_fatigue(data.get("fatigue_before"))

        existing = (
            TrainingSession.query.filter_by(user_id=current_user.id, status="active")
            .order_by(TrainingSession.started_at.desc())
            .first()
        )
        if existing:
            return jsonify({"id": existing.id})

        session = TrainingSessionService.start_session(
            current_user, fatigue_before=fatigue_before
        )

        return jsonify({"id": session.id})
    except Exception as e:
        return _error(e)


@training_api_bp.route("/sessions/<int:session_id>/finish", methods=["POST"])
@login_required
def finish_session(session_id):
    try:
        data = _json_body()
        fatigue_after = _clean_fatigue(data.get("fatigue_after"))

        session = TrainingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id,
            status="active",
        ).first_or_404()

        TrainingSessionService.finish_session(session, fatigue_after)

        return jsonify({"status": "ok", "id": session.id})
    except Exception as e:
        return _error(e)


@training_api_bp.route("/day/<date>")
@login_required
def day_details(date):
    try:
        target = dt.datetime.strptime(date, "%Y-%m-%d").date()

        local_start = dt.datetime.combine(target, dt.time.min, tzinfo=APP_TIMEZONE)

        local_end = dt.datetime.combine(target, dt.time.max, tzinfo=APP_TIMEZONE)

        utc_start = local_start.astimezone(dt.timezone.utc).replace(tzinfo=None)

        utc_end = local_end.astimezone(dt.timezone.utc).replace(tzinfo=None)

        sessions = TrainingSession.query.filter(
            TrainingSession.user_id == current_user.id,
            TrainingSession.started_at >= utc_start,
            TrainingSession.started_at <= utc_end,
        )

        result = []
        for s in sessions:
            exercises = []
            for ex in s.exercises:
                obj = Exercise.query.get(ex.exercise_id)
                if obj:
                    duration = is_duration_exercise(obj)
                    exercises.append(
                        {
                            "name": obj.name,
                            "slug": obj.slug,
                            "measurement_type": measurement_type_of(obj),
                            "sets": ex.sets_done or ex.sets_planned,
                            "reps": (
                                None if duration else ex.reps_done or ex.reps_planned
                            ),
                            "duration_sec": (
                                ex.duration_sec_done or ex.duration_sec_planned
                                if duration
                                else None
                            ),
                            "per_side": is_per_side(obj),
                            "load": ex.load_done or ex.load_planned,
                            "rpe": ex.rpe,
                        }
                    )

            result.append(
                {
                    "session_id": s.id,
                    "fatigue_before": s.fatigue_before,
                    "fatigue_after": s.fatigue_after,
                    "exercises": exercises,
                }
            )

        return jsonify({"sessions": result})
    except Exception as e:
        return _error(e)


@training_api_bp.route("/analytics")
@login_required
def analytics():
    try:
        perf = current_user.performance_states.order_by(
            PerformanceState.created_at.desc()
        ).first()
        rec = current_user.fatigue_state

        performance = {
            "pushups": getattr(perf, "pushups", 0),
            "squats": getattr(perf, "squats", 0),
            "situps": getattr(perf, "situps", 0),
            "plank_sec": getattr(perf, "plank_sec", 0),
            "weight": getattr(perf, "weight", 70),
            "training_load": getattr(perf, "training_load", 0),
            "hip": getattr(perf, "hip", 0),
            "shoulder": getattr(perf, "shoulder", 0),
            "thoracic": getattr(perf, "thoracic", 0),
            "ankle": getattr(perf, "ankle", 0),
        }

        recovery = {
            "sleep": getattr(rec, "sleep", 7),
            "stress": getattr(rec, "stress", 0),
            "soreness": getattr(rec, "soreness", 0),
            "hydration": getattr(rec, "hydration", 2.0),
        }

        result = {
            "performance": performance,
            "recovery": recovery,
            "raw_performance": {
                "pushups": performance["pushups"],
                "squats": performance["squats"],
                "situps": performance["situps"],
            },
        }

        return jsonify(result)

    except Exception as e:
        return _error(e)


@training_api_bp.route("/recommendations")
@login_required
def recommendations():
    try:
        result = build_recommendations(
            user=current_user,
            target_day=dt.date.today(),
        )

        return jsonify(result)
    except Exception as e:
        return _error(e)


@training_api_bp.route("/strength-test", methods=["POST"])
@login_required
def strength_test():
    try:
        data = _json_body()

        pushups = bounded_number(data.get("pushups", 0), 0, 10000, integer=True) or 0
        squats = bounded_number(data.get("squats", 0), 0, 10000, integer=True) or 0
        situps = bounded_number(data.get("situps", 0), 0, 10000, integer=True) or 0

        perf = PerformanceState(
            user_id=current_user.id,
            pushups=pushups,
            squats=squats,
            situps=situps,
        )

        db.session.add(perf)
        db.session.commit()

        return jsonify(
            {
                "status": "ok",
                "raw_performance": {
                    "pushups": pushups,
                    "squats": squats,
                    "situps": situps,
                },
            }
        )
    except Exception as e:
        return _error(e)
