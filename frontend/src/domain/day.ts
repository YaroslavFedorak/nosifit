import type { Habit, MealCategory, PlanEntry, RecoverySnapshot, TrainingSession } from "../api/types";
import { isoDay } from "../lib/format";
import { mealForNow, type DiaryDay } from "./nutrition";

/** What has been recorded today. A part that is null was not recorded: it is never shown as a zero. */
export interface DayState {
  sleep: { minutes: number; start: string | null; end: string | null } | null;
  food: { kcal: number; goal: number | null; meals: MealCategory[] } | null;
  water: { liters: number; goal: number | null } | null;
  workout: { exercises: number; sets: number } | null;
  habits: { done: number; total: number };
  /** Today's exercises of the active plan, while no workout is logged yet. */
  planned: PlanEntry[];
}

export function dayState(input: {
  diary: DiaryDay | undefined;
  water: { amount: number; recommended: number | null } | undefined;
  snapshot: RecoverySnapshot | null | undefined;
  habits: Habit[] | undefined;
  session: TrainingSession | null | undefined;
  planned: PlanEntry[] | undefined;
}): DayState {
  const { diary, water, snapshot, habits = [], session, planned = [] } = input;
  // The newest snapshot may describe an earlier day; only today's counts as last night's sleep.
  const slept = snapshot && snapshot.date === isoDay() && (snapshot.sleep_duration_minutes ?? 0) > 0 ? snapshot : null;
  const meals = (diary?.meals ?? []).filter((meal) => meal.items.length > 0);
  const liters = water?.amount ?? diary?.water ?? 0;
  return {
    sleep: slept ? { minutes: slept.sleep_duration_minutes ?? 0, start: slept.sleep_start, end: slept.sleep_end } : null,
    food: diary && meals.length > 0 ? { kcal: diary.kcal, goal: diary.hasGoals ? diary.kcalGoal : null, meals: meals.map((meal) => meal.category) } : null,
    water: liters > 0 ? { liters, goal: water?.recommended ?? diary?.waterGoal ?? null } : null,
    workout: session && session.exercises.length > 0 ? { exercises: session.totals.exercises, sets: session.totals.sets } : null,
    habits: { done: habits.filter((habit) => habit.completed).length, total: habits.length },
    planned: session ? [] : planned,
  };
}

export type NextStep =
  | { kind: "start" }
  | { kind: "sleep" }
  | { kind: "meal"; meal: MealCategory }
  | { kind: "workout"; exercises: number }
  | { kind: "habits"; left: number }
  | { kind: "done" };

const EVENING = 18;
const NOON = 12;

/**
 * The one thing worth doing now, by the time of day and by what is still
 * missing. `fresh` is an account with nothing recorded ever: it gets an
 * introduction instead of a question about its night.
 */
export function nextStep(state: DayState, hour: number, fresh: boolean): NextStep {
  const nothingToday = !state.sleep && !state.food && !state.water && !state.workout && state.habits.done === 0;
  if (fresh && nothingToday) return { kind: "start" };
  if (!state.sleep && hour < NOON) return { kind: "sleep" };
  const meal = mealForNow(hour);
  if (meal !== "snack" && !state.food?.meals.includes(meal)) return { kind: "meal", meal };
  if (state.planned.length > 0) return { kind: "workout", exercises: state.planned.length };
  const left = state.habits.total - state.habits.done;
  if (left > 0 && hour >= EVENING) return { kind: "habits", left };
  return nothingToday ? { kind: "start" } : { kind: "done" };
}

export type Greeting = "morning" | "day" | "evening";

export const greetingFor = (hour: number): Greeting => (hour < NOON ? "morning" : hour < EVENING ? "day" : "evening");
