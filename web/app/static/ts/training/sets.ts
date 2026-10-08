import type {
    Exercise,
    SetEntry,
    WorkoutExercise
} from "./api.js";

import {
    isDurationExercise
} from "./measurement.js";

const KG_LOAD_TYPES =
    ["external", "machine", "cable"];

// A kg field only where kg means something: barbells, dumbbells, machines,
// cables, or extra weight on a bodyweight exercise that allows it.
export function acceptsLoad(
    exercise: Exercise
): boolean {
    const loadType =
        String(exercise.load_type ?? "");

    return KG_LOAD_TYPES.includes(loadType) ||
        (loadType === "bodyweight" &&
            Boolean(exercise.max_additional_load_kg));
}

function firstNumber(
    value: unknown
): number {
    const match =
        String(value ?? "").match(/\d+/);

    return match ? Number(match[0]) : 0;
}

// The sets of an exercise; items saved before sets existed (sets x a
// "8-12" range) become that many sets of the range's lower bound.
export function entriesOf(
    item: WorkoutExercise
): SetEntry[] {
    if (!item.set_entries?.length) {
        const count =
            Math.max(item.sets || 0, 1);

        const one: SetEntry =
            isDurationExercise(item.exercise)
                ? {
                    duration_sec: firstNumber(item.duration_sec) || 30,
                    load: item.load || 0
                }
                : {
                    reps: firstNumber(item.reps) || 10,
                    load: item.load || 0
                };

        item.set_entries =
            Array.from(
                { length: count },
                () => ({ ...one })
            );
    }

    return item.set_entries;
}

// Keeps sets / reps / load in step with the sets for the rest of the page
// (the server derives the same values on save).
export function syncTotals(
    item: WorkoutExercise
): void {
    const entries =
        entriesOf(item);

    const duration =
        isDurationExercise(item.exercise);

    const counts =
        entries.map(entry =>
            Number(duration ? entry.duration_sec : entry.reps) || 0
        );

    const total =
        counts.reduce((sum, value) => sum + value, 0);

    const mean =
        entries.length ? Math.round(total / entries.length) : 0;

    item.sets =
        entries.length;

    item.load =
        total && !duration
            ? Math.round(
                entries.reduce(
                    (sum, entry, i) => sum + counts[i] * (entry.load || 0),
                    0
                ) / total * 100
            ) / 100
            : entries.length
                ? entries[entries.length - 1].load || 0
                : 0;

    if (duration) {
        item.duration_sec = mean;
        item.reps = null;
    } else {
        item.reps = String(mean);
    }
}
