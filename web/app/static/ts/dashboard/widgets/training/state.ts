interface TrainingExercise {
    id: string;

    databaseId: string | null;

    name: string;

    movement_pattern: string;

    muscles_primary: string[];

    muscles_secondary: string[];

    equipment: string[];

    sets: number;

    reps: any;

    weight: number;

    rpe: number | null;

    completed: boolean;

    [key: string]: any;
}

const exercises: TrainingExercise[] = [];

function createLocalId(): string {
    if (
        typeof crypto !== "undefined" &&
        typeof crypto.randomUUID === "function"
    ) {
        return crypto.randomUUID();
    }

    return (
        Date.now().toString(36) +
        Math.random()
            .toString(36)
            .slice(2)
    );
}

function normalizeDatabaseId(
    value: any
): string | null {
    return value
        ? String(value)
        : null;
}

function normalizeNumber(
    value: any,
    fallback: number | null = 0
): number | null {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return fallback;
    }

    const n = Number(value);

    return Number.isFinite(n)
        ? n
        : fallback;
}

function getDatabaseId(
    exercise: any = {}
): string | null {
    const candidates = [
        exercise.databaseId,
        exercise.database_id,
        exercise.exerciseId,
        exercise.exercise_id,
        exercise.original?.id,
        exercise.exercise?.id,
        exercise.data?.id,
        exercise.id
    ];

    for (const candidate of candidates) {
        const id =
            normalizeDatabaseId(
                candidate
            );

        if (id !== null) {
            return id;
        }
    }

    return null;
}

function getExerciseName(
    exercise: any = {}
): string {
    return (
        exercise.name ||
        exercise.exercise_name ||
        exercise.title ||
        exercise.exercise?.name ||
        exercise.original?.name ||
        "Без назви"
    );
}

function normalizeArray(
    value: any
): string[] {
    if (Array.isArray(value)) {
        return value;
    }

    if (
        typeof value === "string" &&
        value.trim()
    ) {
        return value
            .split(",")
            .map(
                value =>
                    value.trim()
            )
            .filter(Boolean);
    }

    return [];
}

function getMuscles(
    exercise: any,
    field: string
): string[] {
    return normalizeArray(
        exercise[field] ??
        exercise.exercise?.[field] ??
        exercise.original?.[field]
    );
}

function detectCompleted(
    exercise: any
): boolean {
    /*
     * Якщо бекенд повернув
     * done/completed → completed.
     */
    if (
        exercise.completed === true ||
        exercise.done === true
    ) {
        return true;
    }

    /*
     * Якщо є sets_done /
     * reps_done / load_done
     * → completed.
     */
    if (
        exercise.sets_done !==
            undefined ||
        exercise.reps_done !==
            undefined ||
        exercise.load_done !==
            undefined
    ) {
        return true;
    }

    /*
     * Інакше — нова вправа.
     */
    return false;
}

function normalizeExercise(
    exercise: any = {}
): TrainingExercise {
    const databaseId =
        getDatabaseId(exercise);

    const normalizedRpe =
        exercise.rpe !== undefined &&
        exercise.rpe !== null &&
        exercise.rpe !== ""
            ? normalizeNumber(
                exercise.rpe,
                null
            )
            : null;

    return {
        id: createLocalId(),

        databaseId,

        name:
            getExerciseName(
                exercise
            ),

        movement_pattern:
            exercise.movement_pattern ||
            exercise.exercise
                ?.movement_pattern ||
            "",

        muscles_primary:
            getMuscles(
                exercise,
                "muscles_primary"
            ),

        muscles_secondary:
            getMuscles(
                exercise,
                "muscles_secondary"
            ),

        equipment:
            normalizeArray(
                exercise.equipment ??
                exercise.exercise?.equipment ??
                exercise.original?.equipment
            ),

        sets:
            normalizeNumber(
                exercise.sets ??
                exercise.sets_done,
                3
            ) ?? 3,

        reps:
            exercise.reps ??
            exercise.reps_done ??
            "10",

        weight:
            normalizeNumber(
                exercise.weight ??
                exercise.load ??
                exercise.load_done,
                0
            ) ?? 0,

        rpe: normalizedRpe,

        completed:
            detectCompleted(
                exercise
            )
    };
}

export function getExercises(): TrainingExercise[] {
    return exercises;
}

export function getExerciseById(
    id: string
): TrainingExercise | null {
    return (
        exercises.find(
            exercise =>
                String(exercise.id) ===
                String(id)
        ) || null
    );
}

export function addExercise(
    exercise: any
): TrainingExercise | null {
    const normalized =
        normalizeExercise(
            exercise
        );

    if (
        normalized.databaseId === null
    ) {
        console.error(
            "Cannot add exercise without database ID:",
            exercise
        );

        return null;
    }

    exercises.push(normalized);

    return normalized;
}

export function removeExercise(
    id: string
): boolean {
    const index =
        exercises.findIndex(
            exercise =>
                String(exercise.id) ===
                String(id)
        );

    if (index === -1) {
        return false;
    }

    exercises.splice(index, 1);

    return true;
}

export function updateExercise(
    id: string,
    field: string,
    value: any
): boolean {
    const exercise =
        getExerciseById(id);

    if (!exercise) {
        return false;
    }

    exercise[field] = value;

    return true;
}

export function toggleExercise(
    id: string
): boolean {
    const exercise =
        getExerciseById(id);

    if (!exercise) {
        return false;
    }

    exercise.completed =
        !exercise.completed;

    return true;
}

export function replaceExercises(
    newExercises: any[] = []
): void {
    exercises.length = 0;

    if (!Array.isArray(newExercises)) {
        return;
    }

    newExercises.forEach(
        exercise => {
            exercises.push(
                normalizeExercise(
                    exercise
                )
            );
        }
    );
}

export function getCompletedExercises(): TrainingExercise[] {
    return exercises.filter(
        exercise =>
            exercise.completed === true
    );
}

export function clear(): void {
    exercises.length = 0;
}

export function hasExercises(): boolean {
    return exercises.length > 0;
}

export function hasCompletedExercises(): boolean {
    return exercises.some(
        exercise =>
            exercise.completed
    );
}