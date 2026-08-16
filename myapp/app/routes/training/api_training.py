from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from myapp.app import db
from myapp.app.training_engine.models.exercise import Exercise
from myapp.app.training_engine.models.muscle import Muscle
from myapp.app.training_engine.models.equipment import TEEquipment
from myapp.app.training_engine.models.user_pref import UserPreference
from myapp.app.services.training.session_service import TrainingSessionService
from myapp.app.services.training.load_index_service import compute_daily_load_index
from myapp.app.training_engine.training_analysis.recommendations_engine import (
    build_recommendations,
)
from myapp.app.models.training_session import TrainingSession, SessionExercise
from myapp.app.training_engine.models.training_plan import TrainingPlan
from myapp.app.training_engine.models.performance_state import PerformanceState
import datetime as dt

training_api_bp = Blueprint("training_api", __name__, url_prefix="/api/training")


def _error(e):
    current_app.logger.exception("API error")
    return jsonify({"error": "internal_server_error", "message": str(e)}), 500


def _active_plan(user):
    plan = (
        TrainingPlan.query.filter_by(user_id=user.id, is_active=True)
        .order_by(TrainingPlan.id.desc())
        .first()
    )
    return plan


def _today_key():
    return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][dt.date.today().weekday()]


def _plan_days_struct(raw):
    result = {}
    for key, items in raw.items():

        if isinstance(items, dict) and "exercises" in items:
            items = items["exercises"]

        day_ex = []
        for ex in items:
            obj = Exercise.query.get(ex["exercise"]["id"])
            if not obj:
                continue

            day_ex.append(
                {
                    "exercise": {"id": obj.id, "name": obj.name},
                    "sets": ex.get("sets") or 3,
                    "reps": ex.get("reps") or "8-12",
                    "load": ex.get("load") or 0,
                }
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
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))

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
                        "sets": se.sets_done or se.sets_planned or 0,
                        "reps": se.reps_done or se.reps_planned or "8-12",
                        "load": se.load_done or se.load_planned or 0,
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
                        "sets": ex.get("sets") or 3,
                        "reps": ex.get("reps") or "8-12",
                        "load": ex.get("load") or 0,
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
            {
                "name": item["exercise"].name,
                "sets": item["sets"],
                "reps": item["reps"],
                "load": item["load"],
            }
            for item in filtered
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
                    {
                        "name": ex.name,
                        "sets": se.sets_done or se.sets_planned or 0,
                        "reps": se.reps_done or se.reps_planned or "8-12",
                        "load": se.load_done or se.load_planned or 0,
                    }
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
            result["exercises"].append(
                {
                    "name": ex.name,
                    "sets": item.get("sets") or 3,
                    "reps": item.get("reps") or "8-12",
                    "load": item.get("load") or 0,
                }
            )

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

        sessions = (
            TrainingSession.query.filter(
                TrainingSession.user_id == current_user.id,
                TrainingSession.started_at >= dt.datetime.combine(start, dt.time.min),
                TrainingSession.started_at <= dt.datetime.combine(end, dt.time.max),
            )
            .order_by(TrainingSession.started_at.asc())
            .all()
        )

        days = []
        d = start
        today = dt.date.today()

        while d <= end:
            day_sessions = [s for s in sessions if s.started_at.date() == d]
            load_today = sum(s.internal_load or 0 for s in day_sessions)

            if d > today or not day_sessions:
                days.append(
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "load": int(load_today),
                        "percent": 0,
                        "level": 0,
                        "is_today": d == today,
                    }
                )
                d += dt.timedelta(days=1)
                continue

            idx = compute_daily_load_index(current_user, sessions, d)

            days.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "load": int(load_today),
                    "percent": idx["percent"],
                    "level": idx["level"],
                    "is_today": d == today,
                }
            )

            d += dt.timedelta(days=1)

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
        data = request.get_json() or {}
        plan = TrainingPlan(
            user_id=current_user.id,
            name=data.get("name", "Plan"),
            is_active=data.get("is_active", False),
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
        data = request.get_json() or {}

        plan.name = data.get("name", plan.name)
        plan.days = _plan_days_struct(data.get("days", {}))

        if data.get("is_active", plan.is_active):
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


@training_api_bp.route("/sessions/complete", methods=["POST"])
@login_required
def complete_session():
    try:
        existing = TrainingSession.query.filter_by(
            user_id=current_user.id, status="active"
        ).first()

        if existing:
            existing.status = "finished"
            existing.finished_at = dt.datetime.utcnow()
            db.session.commit()

        data = request.get_json() or {}
        raw = data.get("exercises", [])
        exercises = (
            raw if isinstance(raw, list) else [i for v in raw.values() for i in v]
        )

        session = TrainingSession(
            user_id=current_user.id,
            started_at=dt.datetime.utcnow(),
            status="finished",
        )
        db.session.add(session)
        db.session.flush()

        for ex in exercises:
            db.session.add(
                SessionExercise(
                    session_id=session.id,
                    exercise_id=ex["exercise"]["id"],
                    sets_done=ex.get("sets"),
                    reps_done=ex.get("reps"),
                    load_done=ex.get("load"),
                )
            )

        db.session.commit()

        db.session.refresh(session)

        TrainingSessionService._compute_session_load(session)
        db.session.commit()

        TrainingSessionService.update_training_load_from_session(session, current_user)
        return jsonify({"id": session.id})

    except Exception as e:
        return _error(e)


@training_api_bp.route(
    "/sessions/<int:session_id>/exercise/<exercise_id>", methods=["POST"]
)
@login_required
def update_session_exercise(session_id, exercise_id):
    try:
        data = request.get_json() or {}

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
        data = request.get_json() or {}
        fatigue_before = data.get("fatigue_before")

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
        data = request.get_json() or {}
        fatigue_after = data.get("fatigue_after")

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

        sessions = TrainingSession.query.filter(
            TrainingSession.user_id == current_user.id,
            TrainingSession.started_at >= dt.datetime.combine(target, dt.time.min),
            TrainingSession.started_at <= dt.datetime.combine(target, dt.time.max),
        )

        result = []
        for s in sessions:
            exercises = []
            for ex in s.exercises:
                obj = Exercise.query.get(ex.exercise_id)
                if obj:
                    exercises.append(
                        {
                            "name": obj.name,
                            "sets": ex.sets_done or ex.sets_planned,
                            "reps": ex.reps_done or ex.reps_planned,
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
            "weight": getattr(current_user, "weight", 70),
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
        sessions = (
            TrainingSession.query.filter_by(user_id=current_user.id)
            .order_by(TrainingSession.started_at.desc())
            .all()
        )

        result = build_recommendations(
            user=current_user,
            sessions=sessions,
            target_day=dt.date.today(),
        )

        return jsonify(result)
    except Exception as e:
        return _error(e)


@training_api_bp.route("/strength-test", methods=["POST"])
@login_required
def strength_test():
    try:
        data = request.get_json() or {}

        pushups = int(data.get("pushups", 0))
        squats = int(data.get("squats", 0))
        situps = int(data.get("situps", 0))

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
