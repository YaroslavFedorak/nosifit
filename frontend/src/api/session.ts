import type { ExerciseOption, LoggedExercise, SetEntry } from "./types";

const DEFAULT_SETS = 3;
const DEFAULT_REPS = 10;
const DEFAULT_SECONDS = 30;

export const isTimed = (exercise: Pick<LoggedExercise, "measurement_type">): boolean => exercise.measurement_type === "duration";

/** The sets of an exercise, one by one. Older sessions only stored sets, reps and weight. */
export function entriesOf(exercise: LoggedExercise): SetEntry[] {
  if (exercise.set_entries?.length) return exercise.set_entries;
  const count = Math.max(1, exercise.sets || 1);
  const load = exercise.load ?? 0;
  const entry: SetEntry = isTimed(exercise)
    ? { duration_sec: exercise.duration_sec ?? DEFAULT_SECONDS, load }
    : { reps: Number.parseInt(String(exercise.reps ?? DEFAULT_REPS), 10) || DEFAULT_REPS, load };
  return Array.from({ length: count }, () => ({ ...entry }));
}

/** A new exercise starts from what the user did last time, or from three easy sets. */
export function exerciseFromOption(option: ExerciseOption): LoggedExercise {
  const timed = option.measurement_type === "duration";
  const previous = option.last?.set_entries;
  const entries: SetEntry[] = previous?.length
    ? previous.map((entry) => ({ ...entry }))
    : Array.from({ length: DEFAULT_SETS }, () =>
        timed
          ? { duration_sec: option.last?.duration_sec ?? DEFAULT_SECONDS, load: 0 }
          : { reps: DEFAULT_REPS, load: option.last?.load ?? 0 },
      );
  const first = entries[0];
  return {
    id: option.id,
    name: option.name,
    slug: option.slug,
    measurement_type: option.measurement_type,
    sets: entries.length,
    reps: first?.reps ?? null,
    duration_sec: first?.duration_sec ?? null,
    load: first?.load ?? 0,
    per_side: option.per_side,
    set_entries: entries,
  };
}

/** Sum of reps × weight over all sets of reps-based exercises. */
export function totalVolume(exercises: LoggedExercise[]): number {
  return exercises.reduce(
    (sum, exercise) =>
      sum + (isTimed(exercise) ? 0 : entriesOf(exercise).reduce((acc, entry) => acc + (entry.reps ?? 0) * (entry.load ?? 0), 0)),
    0,
  );
}

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
