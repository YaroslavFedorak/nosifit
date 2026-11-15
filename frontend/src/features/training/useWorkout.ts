import { useRef } from "react";
import { useSaveSession } from "../../api/mutations";
import { useTrainingSession } from "../../api/queries";
import type { LoggedExercise, SetEntry } from "../../api/types";
import { entriesOf, isTimed } from "../../domain/training";
import type { I18n } from "../../i18n";
import { num } from "../../lib/format";

/**
 * Today's workout and the one way to change it: the whole list is sent and
 * replaces what the server has. The session id is remembered from the first
 * save, so a second change made before the list reloads edits the same
 * session instead of starting another.
 */
export function useWorkout() {
  const session = useTrainingSession();
  const save = useSaveSession();
  const id = useRef<number | null>(null);
  if (session.data?.id) id.current = session.data.id;
  if (session.data === null && !save.isPending) id.current = null;

  const persist = async (exercises: LoggedExercise[]): Promise<void> => {
    const saved = await save.mutateAsync({ sessionId: id.current, exercises });
    id.current = saved.id ?? null;
  };

  return {
    loading: session.isPending,
    failed: session.isError,
    retry: () => void session.refetch(),
    exercises: session.data?.exercises ?? [],
    persist,
    busy: save.isPending,
  };
}

/** One set in words: "10 × 40 кг", "12 повт.", "30 с". */
export function setLabel(entry: SetEntry, timed: boolean, t: I18n["t"]): string {
  const load = entry.load ?? 0;
  if (timed) return load > 0 ? `${entry.duration_sec ?? 0} ${t("unit.s")} × ${num(load)} ${t("unit.kg")}` : `${entry.duration_sec ?? 0} ${t("unit.s")}`;
  return load > 0 ? `${entry.reps ?? 0} × ${num(load)} ${t("unit.kg")}` : `${entry.reps ?? 0} ${t("unit.reps")}`;
}

/** An exercise's sets in one line: "3 × 10 × 40 кг" when they match, each set otherwise. */
export function setsLabel(exercise: LoggedExercise, t: I18n["t"]): string {
  const entries = entriesOf(exercise);
  const timed = isTimed(exercise);
  const labels = entries.map((entry) => setLabel(entry, timed, t));
  const first = labels[0];
  if (first && labels.every((label) => label === first)) return `${entries.length} × ${first}`;
  return labels.join(", ");
}

/** A planned line: "3 × 10" or "3 × 30 с". */
export function planLabel(entry: { sets: number | null; reps: string | number | null; duration_sec: number | null; measurement_type: string }, t: I18n["t"]): string {
  const sets = entry.sets ?? 3;
  return isTimed(entry) ? `${sets} × ${entry.duration_sec ?? 30} ${t("unit.s")}` : `${sets} × ${entry.reps ?? 10}`;
}
