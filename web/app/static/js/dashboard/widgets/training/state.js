const STORAGE_KEY = "dashboard_training_exercises";
const STORAGE_DATE_KEY = "dashboard_training_date";
const exercises = [];
function createLocalId() {
    if (typeof crypto !== "undefined" &&
        typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return (Date.now().toString(36) +
        Math.random()
            .toString(36)
            .slice(2));
}
function getTodayKey() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function normalizeDatabaseId(value) {
    return value
        ? String(value)
        : null;
}
function normalizeNumber(value, fallback = 0) {
    if (value === null ||
        value === undefined ||
        value === "") {
        return fallback;
    }
    const number = Number(value);
    return Number.isFinite(number)
        ? number
        : fallback;
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
    for (const candidate of candidates) {
        const id = normalizeDatabaseId(candidate);
        if (id !== null) {
            return id;
        }
    }
    return null;
}
function getExerciseName(exercise = {}) {
    return (exercise.name ||
        exercise.exercise_name ||
        exercise.title ||
        exercise.exercise?.name ||
        exercise.original?.name ||
        "Без назви");
}
function normalizeArray(value) {
    if (Array.isArray(value)) {
        return value;
    }
    if (typeof value === "string" &&
        value.trim()) {
        return value
            .split(",")
            .map(value => value.trim())
            .filter(Boolean);
    }
    return [];
}
function getMuscles(exercise, field) {
    return normalizeArray(exercise[field] ??
        exercise.exercise?.[field] ??
        exercise.original?.[field]);
}
function detectCompleted(exercise) {
    if (exercise.completed === true ||
        exercise.done === true) {
        return true;
    }
    if (exercise.sets_done !== undefined ||
        exercise.reps_done !== undefined ||
        exercise.load_done !== undefined) {
        return true;
    }
    return false;
}
function normalizeExercise(exercise = {}) {
    const databaseId = getDatabaseId(exercise);
    const normalizedRpe = exercise.rpe !== undefined &&
        exercise.rpe !== null &&
        exercise.rpe !== ""
        ? normalizeNumber(exercise.rpe, null)
        : null;
    return {
        id: typeof exercise.id === "string"
            ? exercise.id
            : createLocalId(),
        databaseId,
        name: getExerciseName(exercise),
        movement_pattern: exercise.movement_pattern ||
            exercise.exercise
                ?.movement_pattern ||
            "",
        muscles_primary: getMuscles(exercise, "muscles_primary"),
        muscles_secondary: getMuscles(exercise, "muscles_secondary"),
        equipment: normalizeArray(exercise.equipment ??
            exercise.exercise?.equipment ??
            exercise.original?.equipment),
        sets: normalizeNumber(exercise.sets ??
            exercise.sets_done, 3) ?? 3,
        reps: exercise.reps ??
            exercise.reps_done ??
            "10",
        weight: normalizeNumber(exercise.weight ??
            exercise.load ??
            exercise.load_done, 0) ?? 0,
        rpe: normalizedRpe,
        completed: detectCompleted(exercise)
    };
}
function persist() {
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(exercises));
        window.localStorage.setItem(STORAGE_DATE_KEY, getTodayKey());
    }
    catch {
        return;
    }
}
function loadPersisted() {
    try {
        const savedDate = window.localStorage.getItem(STORAGE_DATE_KEY);
        if (savedDate !==
            getTodayKey()) {
            window.localStorage.removeItem(STORAGE_KEY);
            window.localStorage.removeItem(STORAGE_DATE_KEY);
            return;
        }
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return;
        }
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
            return;
        }
        exercises.length = 0;
        parsed.forEach(exercise => {
            const normalized = normalizeExercise(exercise);
            if (normalized.databaseId !==
                null) {
                exercises.push(normalized);
            }
        });
    }
    catch {
        exercises.length = 0;
    }
}
export function initState() {
    loadPersisted();
}
export function getExercises() {
    return exercises;
}
export function getExerciseById(id) {
    return (exercises.find(exercise => String(exercise.id) ===
        String(id)) || null);
}
export function addExercise(exercise) {
    const normalized = normalizeExercise(exercise);
    if (normalized.databaseId ===
        null) {
        console.error("Cannot add exercise without database ID:", exercise);
        return null;
    }
    exercises.push(normalized);
    persist();
    return normalized;
}
export function removeExercise(id) {
    const index = exercises.findIndex(exercise => String(exercise.id) ===
        String(id));
    if (index === -1) {
        return false;
    }
    exercises.splice(index, 1);
    persist();
    return true;
}
export function updateExercise(id, field, value) {
    const exercise = getExerciseById(id);
    if (!exercise) {
        return false;
    }
    exercise[field] =
        value;
    persist();
    return true;
}
export function toggleExercise(id) {
    const exercise = getExerciseById(id);
    if (!exercise) {
        return false;
    }
    exercise.completed =
        !exercise.completed;
    persist();
    return true;
}
export function replaceExercises(newExercises = []) {
    exercises.length = 0;
    if (!Array.isArray(newExercises)) {
        persist();
        return;
    }
    newExercises.forEach(exercise => {
        const normalized = normalizeExercise(exercise);
        if (normalized.databaseId !==
            null) {
            exercises.push(normalized);
        }
    });
    persist();
}
export function getCompletedExercises() {
    return exercises.filter(exercise => exercise.completed === true);
}
export function clear() {
    exercises.length = 0;
    try {
        window.localStorage.removeItem(STORAGE_KEY);
        window.localStorage.removeItem(STORAGE_DATE_KEY);
    }
    catch {
        return;
    }
}
export function hasExercises() {
    return exercises.length > 0;
}
export function hasCompletedExercises() {
    return exercises.some(exercise => exercise.completed);
}
