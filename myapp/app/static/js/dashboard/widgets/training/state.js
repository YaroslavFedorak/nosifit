const exercises = [];

function createLocalId() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function normalizeDatabaseId(value) {
    return value ? String(value) : null;
}

function normalizeNumber(value, fallback = 0) {
    if (value === null || value === undefined || value === "") return fallback;
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
}

function getDatabaseId(exercise = {}) {
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
    for (const c of candidates) {
        const id = normalizeDatabaseId(c);
        if (id !== null) return id;
    }
    return null;
}

function getExerciseName(exercise = {}) {
    return (
        exercise.name ||
        exercise.exercise_name ||
        exercise.title ||
        exercise.exercise?.name ||
        exercise.original?.name ||
        "Без назви"
    );
}

function normalizeArray(value) {
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value.trim()) {
        return value.split(",").map(v => v.trim()).filter(Boolean);
    }
    return [];
}

function getMuscles(exercise, field) {
    return normalizeArray(
        exercise[field] ??
        exercise.exercise?.[field] ??
        exercise.original?.[field]
    );
}

function detectCompleted(exercise) {
    // Якщо бекенд повернув done/completed → це completed
    if (exercise.completed === true || exercise.done === true) return true;

    // Якщо є sets_done / reps_done / load_done → це completed
    if (
        exercise.sets_done !== undefined ||
        exercise.reps_done !== undefined ||
        exercise.load_done !== undefined
    ) {
        return true;
    }

    // Інакше — нова вправа, вона не completed
    return false;
}

function normalizeExercise(exercise = {}) {
    const databaseId = getDatabaseId(exercise);

    return {
        id: createLocalId(),
        databaseId,
        name: getExerciseName(exercise),

        movement_pattern:
            exercise.movement_pattern ||
            exercise.exercise?.movement_pattern ||
            "",

        muscles_primary: getMuscles(exercise, "muscles_primary"),
        muscles_secondary: getMuscles(exercise, "muscles_secondary"),

        equipment: normalizeArray(
            exercise.equipment ??
            exercise.exercise?.equipment ??
            exercise.original?.equipment
        ),

        sets: normalizeNumber(exercise.sets ?? exercise.sets_done, 3),
        reps: exercise.reps ?? exercise.reps_done ?? "10",
        weight: normalizeNumber(exercise.weight ?? exercise.load ?? exercise.load_done, 0),

        rpe:
            exercise.rpe !== undefined &&
            exercise.rpe !== null &&
            exercise.rpe !== ""
                ? normalizeNumber(exercise.rpe, null)
                : null,

        completed: detectCompleted(exercise)
    };
}

export function getExercises() {
    return exercises;
}

export function getExerciseById(id) {
    return exercises.find(ex => String(ex.id) === String(id)) || null;
}

export function addExercise(exercise) {
    const normalized = normalizeExercise(exercise);
    if (normalized.databaseId === null) {
        console.error("Cannot add exercise without database ID:", exercise);
        return null;
    }
    exercises.push(normalized);
    return normalized;
}

export function removeExercise(id) {
    const index = exercises.findIndex(ex => String(ex.id) === String(id));
    if (index === -1) return false;
    exercises.splice(index, 1);
    return true;
}

export function updateExercise(id, field, value) {
    const exercise = getExerciseById(id);
    if (!exercise) return false;
    exercise[field] = value;
    return true;
}

export function toggleExercise(id) {
    const exercise = getExerciseById(id);
    if (!exercise) return false;
    exercise.completed = !exercise.completed;
    return true;
}

export function replaceExercises(newExercises = []) {
    exercises.length = 0;
    if (!Array.isArray(newExercises)) return;
    newExercises.forEach(ex => {
        exercises.push(normalizeExercise(ex));
    });
}

export function getCompletedExercises() {
    return exercises.filter(ex => ex.completed === true);
}

export function clear() {
    exercises.length = 0;
}

export function hasExercises() {
    return exercises.length > 0;
}

export function hasCompletedExercises() {
    return exercises.some(ex => ex.completed);
}
