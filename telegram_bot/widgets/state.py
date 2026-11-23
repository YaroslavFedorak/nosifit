"""The user's day as the Today card's chat state.

The card draws only what is recorded (a part with nothing logged is left out,
never shown as zero) and asks one question: the next step, by the same rules
as the website's Today screen (frontend/src/domain/day.ts). Every text is
formatted here, in the user's language, so the card's script stays small.
"""

import json
import time
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram_bot.i18n import current_language, plural, t

# Telegram keeps at most 1024 bytes of chat state per message.
MAX_STATE = 1024
HABITS_SHOWN = 6
HABIT_NAME = 28
WEEK = 7
EVENING = 18

TRANSLATIONS = Path(__file__).resolve().parents[2] / "shared" / "translations"


@lru_cache(maxsize=8)
def _habit_names(language: str) -> dict:
    try:
        with (TRANSLATIONS / language / "recovery.json").open(encoding="utf-8") as file:
            habits = json.load(file).get("habits", {})
    except (OSError, ValueError):
        return {}
    return habits if isinstance(habits, dict) else {}


def habit_name(habit: dict) -> str:
    entry = _habit_names(current_language()).get(habit.get("slug") or "")
    name = entry.get("name") if isinstance(entry, dict) else None
    return str(name or habit.get("name") or "")


def number(value: float, digits: int = 0) -> str:
    """One number format everywhere: a dot for decimals, a thin space between thousands."""
    text = f"{value:,.{digits}f}".replace(",", " ")
    return text.rstrip("0").rstrip(".") if digits else text


def meal_for_hour(hour: int) -> str:
    if hour < 11:
        return "breakfast"
    if hour < 16:
        return "lunch"
    if hour < 21:
        return "dinner"
    return "snack"


def day_caption(today: date) -> str:
    weekday = t("w.weekdays").split("|")[today.weekday()]
    month = t("w.months").split("|")[today.month - 1]
    return t("w.caption", date=f"{weekday}, {today.day} {month}")


def _local_time(value: str | None, zone: ZoneInfo) -> str | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is not None:
        moment = moment.astimezone(zone)
    return moment.strftime("%H:%M")


def _food(day: dict | None) -> list | None:
    meals = [meal for meal in (day or {}).get("meals", []) if meal.get("items")]
    if not meals:
        return None
    kcal = float(day.get("kcal") or 0)
    goal = float(day.get("kcal_goal") or 0) if day.get("goals_available") else 0
    if goal > 0:
        return [t("w.kcal_of", n=number(kcal), goal=number(goal)), round(kcal / goal, 3)]
    return [t("w.kcal", n=number(kcal)), None]


def _water(day: dict | None) -> list | None:
    liters = float((day or {}).get("water") or 0)
    if liters <= 0:
        return None
    goal = float((day or {}).get("water_goal") or 0)
    if goal > 0:
        return [t("w.water_of", n=number(liters, 2), goal=number(goal, 2)), round(liters / goal, 3)]
    return [t("w.water", n=number(liters, 2)), None]


def _sleep(snapshot: dict | None, today: date, zone: ZoneInfo) -> list | None:
    # The newest snapshot may describe an earlier day; only today's is last night's sleep.
    if not snapshot or snapshot.get("date") != today.isoformat():
        return None
    minutes = int(snapshot.get("sleep_duration_minutes") or 0)
    if minutes <= 0:
        return None
    start = _local_time(snapshot.get("sleep_start"), zone)
    end = _local_time(snapshot.get("sleep_end"), zone)
    return [t("w.sleep", h=minutes // 60, m=minutes % 60), f"{start}–{end}" if start and end else ""]


def _workout(session: dict | None) -> str | None:
    if not session or not session.get("exercises"):
        return None
    totals = session.get("totals") or {}
    exercises = int(totals.get("exercises") or len(session["exercises"]))
    sets = int(totals.get("sets") or 0)
    text = f"{exercises} {plural(exercises, 'tr.plural_exercises')}"
    if sets:
        text += f", {sets} {plural(sets, 'tr.plural_sets')}"
    return text


def _week(stats: dict | None, today: date) -> tuple[list | None, str]:
    values = list(((stats or {}).get("kcal") or {}).get("values") or [])[-WEEK:]
    if len(values) != WEEK or not any(values):
        return None, ""
    top = max([float(v) for v in values if v] + [float((stats or {}).get("goal_kcal") or 0)])
    letters = t("w.days")
    week = []
    for index, value in enumerate(values):
        day = today - timedelta(days=WEEK - 1 - index)
        week.append([letters[day.weekday()], round(float(value) / top, 3) if value else None])
    average = (stats or {}).get("avg_kcal")
    return week, t("w.avg", n=number(float(average))) if average else ""


def next_step(*, meals: set, recorded: bool, habits_done: int, habits_total: int, hour: int, fresh: bool) -> str:
    nothing = not recorded and habits_done == 0
    if fresh and nothing:
        return t("w.next.start")
    meal = meal_for_hour(hour)
    if meal != "snack" and meal not in meals:
        return t(f"w.next.{meal}")
    if habits_total > habits_done and hour >= EVENING:
        return t("w.next.habits")
    return t("w.next.open") if nothing else t("w.next.done")


def build_state(
    *,
    day: dict | None,
    snapshot: dict | None,
    habits: list[dict],
    session: dict | None,
    stats: dict | None,
    now: datetime,
) -> str:
    """The chat state of the card, at most MAX_STATE bytes of JSON."""
    zone = now.tzinfo if isinstance(now.tzinfo, ZoneInfo) else ZoneInfo("UTC")
    today = now.date()
    food = _food(day)
    water = _water(day)
    sleep = _sleep(snapshot, today, zone)
    workout = _workout(session)
    week, average = _week(stats, today)
    done = sum(1 for habit in habits if habit.get("completed"))

    state: dict = {
        # Newer state wins in the card: an answer and an edit may arrive in either order.
        "r": int(time.time() * 1000),
        "n": next_step(
            meals={meal.get("category") for meal in (day or {}).get("meals", []) if meal.get("items")},
            recorded=bool(food or water or sleep or workout),
            habits_done=done,
            habits_total=len(habits),
            hour=now.hour,
            fresh=week is None and not habits,
        ),
    }
    if food:
        state["f"] = food
    if water:
        state["w"] = water
    if sleep:
        state["s"] = sleep
    if workout:
        state["t"] = workout
    if week:
        state["k"], state["ka"] = week, average

    shown = [
        [habit["user_habit_id"], habit_name(habit)[:HABIT_NAME], 1 if habit.get("completed") else 0]
        for habit in habits
        if isinstance(habit.get("user_habit_id"), int)
    ][:HABITS_SHOWN]
    if shown:
        # The card says how many more there are; it may show fewer still to fit its height.
        state["hc"] = t("w.habits_count", done=done, total=len(habits))
        state["hn"] = len(habits)
    # Long habit names in a long list are what can outgrow the limit: send fewer.
    while True:
        if shown:
            state["h"] = shown
        text = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        if len(text.encode("utf-8")) <= MAX_STATE or not shown:
            break
        shown = shown[:-1]
        if not shown:
            for key in ("h", "hc", "hn"):
                state.pop(key, None)
    if len(text.encode("utf-8")) > MAX_STATE:
        state.pop("k", None)
        state.pop("ka", None)
        text = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    return text
