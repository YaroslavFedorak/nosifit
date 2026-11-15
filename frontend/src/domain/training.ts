import type { ExerciseOption, LoggedExercise, Plan, PlanDay, PlanEntry, SetEntry, Weekday } from "../api/types";
import { WEEKDAYS } from "../api/types";

const DEFAULT_SETS = 3;
const DEFAULT_REPS = 10;
const DEFAULT_SECONDS = 30;

export const isTimed = (exercise: { measurement_type: string }): boolean => exercise.measurement_type === "duration";

const wholeReps = (value: string | number | null | undefined): number => Number.parseInt(String(value ?? DEFAULT_REPS), 10) || DEFAULT_REPS;

/** The sets of an exercise, one by one. Older sessions only stored sets, reps and weight. */
export function entriesOf(exercise: LoggedExercise): SetEntry[] {
  if (exercise.set_entries?.length) return exercise.set_entries;
  const count = Math.max(1, exercise.sets || 1);
  const load = exercise.load ?? 0;
  const entry: SetEntry = isTimed(exercise)
    ? { duration_sec: exercise.duration_sec ?? DEFAULT_SECONDS, load }
    : { reps: wholeReps(exercise.reps), load };
  return Array.from({ length: count }, () => ({ ...entry }));
}

/** The same exercise with a new list of sets; the summary fields follow the first set. */
export function withEntries(exercise: LoggedExercise, entries: SetEntry[]): LoggedExercise {
  const first = entries[0];
  return {
    ...exercise,
    set_entries: entries,
    sets: entries.length,
    reps: first?.reps ?? null,
    duration_sec: first?.duration_sec ?? null,
    load: first?.load ?? 0,
  };
}

/** A new exercise starts from what the user did last time, or from three easy sets. */
export function exerciseFromOption(option: ExerciseOption): LoggedExercise {
  const timed = isTimed(option);
  const previous = option.last?.set_entries;
  const entries: SetEntry[] = previous?.length
    ? previous.map((entry) => ({ ...entry }))
    : Array.from({ length: DEFAULT_SETS }, () =>
        timed ? { duration_sec: option.last?.duration_sec ?? DEFAULT_SECONDS, load: 0 } : { reps: DEFAULT_REPS, load: option.last?.load ?? 0 },
      );
  return withEntries(
    {
      id: String(option.id),
      name: option.name,
      slug: option.slug,
      measurement_type: option.measurement_type,
      sets: entries.length,
      reps: null,
      duration_sec: null,
      load: 0,
      per_side: option.per_side,
      accepts_load: option.accepts_load,
    },
    entries,
  );
}

/** A planned exercise turned into one to log: its planned sets become the starting sets. */
export function exerciseFromPlan(entry: PlanEntry): LoggedExercise {
  const timed = isTimed(entry);
  const count = Math.max(1, entry.sets ?? DEFAULT_SETS);
  const load = entry.load ?? 0;
  const one: SetEntry = timed ? { duration_sec: entry.duration_sec ?? DEFAULT_SECONDS, load } : { reps: wholeReps(entry.reps), load };
  return withEntries(
    {
      id: String(entry.exercise.id),
      name: entry.exercise.name,
      slug: entry.exercise.slug,
      measurement_type: entry.measurement_type,
      sets: count,
      reps: null,
      duration_sec: null,
      load,
      per_side: entry.per_side,
    },
    Array.from({ length: count }, () => ({ ...one })),
  );
}

/** A catalog exercise as a line of a plan, with a plain starting prescription. */
export function planEntryFromOption(option: ExerciseOption): PlanEntry {
  const timed = isTimed(option);
  return {
    exercise: { id: option.id, name: option.name, slug: option.slug, measurement_type: option.measurement_type },
    measurement_type: option.measurement_type,
    sets: DEFAULT_SETS,
    reps: timed ? null : String(DEFAULT_REPS),
    duration_sec: timed ? DEFAULT_SECONDS : null,
    per_side: option.per_side,
    load: 0,
  };
}

/** Sum of reps × weight over all sets of reps-based exercises. */
export function totalVolume(exercises: LoggedExercise[]): number {
  return exercises.reduce(
    (sum, exercise) => sum + (isTimed(exercise) ? 0 : entriesOf(exercise).reduce((acc, entry) => acc + (entry.reps ?? 0) * (entry.load ?? 0), 0)),
    0,
  );
}

export const totalSets = (exercises: LoggedExercise[]): number => exercises.reduce((sum, exercise) => sum + entriesOf(exercise).length, 0);

/** The body POST /api/training/sessions/complete expects: today's whole workout, replaced. */
export function sessionPayload(sessionId: number | null, exercises: LoggedExercise[]) {
  return {
    session_id: sessionId,
    exercises: exercises.map((exercise) => {
      const entries = entriesOf(exercise);
      const first = entries[0];
      const timed = isTimed(exercise);
      return {
        exercise: { id: exercise.id },
        sets: entries.length,
        ...(timed ? { duration_sec: first?.duration_sec ?? DEFAULT_SECONDS } : { reps: String(first?.reps ?? DEFAULT_REPS) }),
        load: first?.load ?? 0,
        set_entries: entries.map((entry) =>
          timed ? { duration_sec: entry.duration_sec, load: entry.load ?? 0 } : { reps: entry.reps, load: entry.load ?? 0 },
        ),
        ...(exercise.rpe != null ? { rpe: exercise.rpe } : {}),
      };
    }),
  };
}

/* Plans */

/** The exercises of a plan's day; a missing day and an older bare list both work. */
export function planDayEntries(plan: Pick<Plan, "days"> | null | undefined, key: Weekday): PlanEntry[] {
  const day = plan?.days?.[key];
  if (!day) return [];
  return Array.isArray(day) ? day : (day.exercises ?? []);
}

/** The body the plan routes expect for one day. */
export function planDayPayload(entries: PlanEntry[]): PlanDay {
  return {
    exercises: entries.map((entry) => ({
      ...entry,
      exercise: { ...entry.exercise },
    })),
  };
}

export const todayKey = (date: Date = new Date()): Weekday => WEEKDAYS[(date.getDay() + 6) % 7] ?? "mon";

export const trainingDaysOf = (plan: Pick<Plan, "days">): number => WEEKDAYS.filter((key) => planDayEntries(plan, key).length > 0).length;
