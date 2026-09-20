import type {
    Exercise,
    WorkoutExercise
} from "./api.js";

import {
    trainingStore
} from "./store.js";

const STORAGE_KEY =
    "dashboard_training_exercises";

const STORAGE_DATE_KEY =
    "dashboard_training_date";

export type DailyTrainingExercise = {
    id: string;
    databaseId: string | null;
    name: string;
    exercise: Exercise;
    sets: number;
    reps: string | number;
    load: number;
    weight: number;
    rpe: number | null;
    done: boolean;
    completed: boolean;
    fromPlan: boolean;
};

function getTodayKey(): string {
    const date =
        new Date();

    const year =
        date.getFullYear();

    const month =
        String(
            date.getMonth() + 1
        ).padStart(2, "0");

    const day =
        String(
            date.getDate()
        ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function createLocalId(): string {
    if (
        typeof crypto !== "undefined" &&
        typeof crypto.randomUUID === "function"
    ) {
        return crypto.randomUUID();
    }

    return `${Date.now()}-${Math.random()
        .toString(36)
        .slice(2)}`;
}

function normalizeExercise(
    item: Partial<DailyTrainingExercise>
): DailyTrainingExercise | null {
    if (
        !item ||
        typeof item !== "object"
    ) {
        return null;
    }

    const source =
        item.exercise &&
        typeof item.exercise === "object"
            ? item.exercise
            : null;

    const databaseId =
        item.databaseId != null
            ? String(
                item.databaseId
            )
            : source?.id != null
                ? String(
                    source.id
                )
                : null;

    const id =
        item.id != null
            ? String(
                item.id
            )
            : databaseId ??
              createLocalId();

    const exercise: Exercise = {
        ...(source ?? {}),
        id:
            databaseId ??
            source?.id ??
            id,
        name:
            item.name ??
            source?.name ??
            "Вправа"
    };

    const name =
        typeof item.name === "string" &&
        item.name.trim()
            ? item.name
            : exercise.name;

    const load =
        Number(
            item.load ??
            item.weight ??
            0
        ) || 0;

    const completed =
        Boolean(
            item.completed ??
            item.done
        );

    return {
        id,
        databaseId,
        name,
        exercise,
        sets:
            Number(
                item.sets
            ) || 0,
        reps:
            item.reps ??
            "8-12",
        load,
        weight: load,
        rpe:
            item.rpe != null
                ? Number(
                    item.rpe
                )
                : null,
        done:
            completed,
        completed,
        fromPlan:
            Boolean(
                item.fromPlan
            )
    };
}

export function getDailyExercises(): DailyTrainingExercise[] {
    try {
        const savedDate =
            localStorage.getItem(
                STORAGE_DATE_KEY
            );

        if (
            savedDate !==
            getTodayKey()
        ) {
            localStorage.removeItem(
                STORAGE_KEY
            );

            localStorage.removeItem(
                STORAGE_DATE_KEY
            );

            return [];
        }

        const raw =
            localStorage.getItem(
                STORAGE_KEY
            );

        if (!raw) {
            return [];
        }

        const parsed =
            JSON.parse(raw);

        if (!Array.isArray(parsed)) {
            return [];
        }

        return parsed
            .map(
                normalizeExercise
            )
            .filter(
                (
                    item
                ): item is DailyTrainingExercise =>
                    item !== null
            );
    } catch {
        return [];
    }
}

export function persistWorkout(
    exercises: WorkoutExercise[]
): void {
    const normalized =
        exercises
            .map(item =>
                normalizeExercise({
                    id:
                        item.exercise?.id != null
                            ? String(
                                item.exercise.id
                            )
                            : undefined,
                    databaseId:
                        item.exercise?.id != null
                            ? String(
                                item.exercise.id
                            )
                            : null,
                    name:
                        item.exercise?.name ??
                        "Вправа",
                    exercise:
                        item.exercise,
                    sets:
                        item.sets,
                    reps:
                        item.reps,
                    load:
                        item.load,
                    weight:
                        item.load,
                    rpe:
                        null,
                    done:
                        item.done,
                    completed:
                        item.done,
                    fromPlan:
                        item.fromPlan
                })
            )
            .filter(
                (
                    item
                ): item is DailyTrainingExercise =>
                    item !== null
            );

    try {
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(
                normalized
            )
        );

        localStorage.setItem(
            STORAGE_DATE_KEY,
            getTodayKey()
        );
    } catch {
        return;
    }
}

export function initDailyState(): void {
    const saved =
        getDailyExercises();

    trainingStore.workout =
        saved.map(item => ({
            exercise:
                item.exercise,
            sets:
                item.sets,
            reps:
                item.reps,
            load:
                item.load,
            done:
                item.done ||
                item.completed,
            fromPlan:
                item.fromPlan
        }));
}