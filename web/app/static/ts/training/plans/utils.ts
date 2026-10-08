import type { PlanExercise } from "../api.js";

export function formatSets(
    list: PlanExercise[]
): number {
    return list.reduce(
        (total, exercise) =>
            total +
            Number(exercise.sets || 0),
        0
    );
}

export function formatCount(
    list: PlanExercise[]
): number {
    return list.length;
}