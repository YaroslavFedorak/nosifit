import { trainingStore } from "./store.js";
import { t } from "../i18n/index.js";
import { defaultPrescription, isDurationExercise } from "./measurement.js";
const STORAGE_KEY = "dashboard_training_exercises";
const STORAGE_DATE_KEY = "dashboard_training_date";
// Session created by today's first "save workout"; later saves update it.
const STORAGE_SESSION_KEY = "dashboard_training_session_id";
function getTodayKey() {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function createLocalId() {
    if (typeof crypto !== "undefined" &&
        typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random()
        .toString(36)
        .slice(2)}`;
}
function normalizeExercise(item) {
    if (!item ||
        typeof item !== "object") {
        return null;
    }
    const source = item.exercise &&
        typeof item.exercise === "object"
        ? item.exercise
        : null;
    const databaseId = item.databaseId != null
        ? String(item.databaseId)
        : source?.id != null
            ? String(source.id)
            : null;
    const id = item.id != null
        ? String(item.id)
        : databaseId ??
            createLocalId();
    const exercise = {
        ...(source ?? {}),
        id: databaseId ??
            source?.id ??
            id,
        name: item.name ??
            source?.name ??
            t("exercise.fallback")
    };
    const name = typeof item.name === "string" &&
        item.name.trim()
        ? item.name
        : exercise.name;
    const load = Number(item.load ??
        item.weight ??
        0) || 0;
    const completed = Boolean(item.completed ??
        item.done);
    return {
        id,
        databaseId,
        name,
        exercise,
        sets: Number(item.sets) || 0,
        reps: item.reps ??
            null,
        duration_sec: item.duration_sec != null
            ? Number(item.duration_sec) || null
            : null,
        load,
        weight: load,
        rpe: item.rpe != null
            ? Number(item.rpe)
            : null,
        set_entries: Array.isArray(item.set_entries)
            ? item.set_entries
            : null,
        done: completed,
        completed,
        fromPlan: Boolean(item.fromPlan)
    };
}
export function getDailyExercises() {
    try {
        const savedDate = localStorage.getItem(STORAGE_DATE_KEY);
        if (savedDate !==
            getTodayKey()) {
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem(STORAGE_DATE_KEY);
            localStorage.removeItem(STORAGE_SESSION_KEY);
            return [];
        }
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return [];
        }
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
            return [];
        }
        return parsed
            .map(normalizeExercise)
            .filter((item) => item !== null);
    }
    catch {
        return [];
    }
}
export function persistWorkout(exercises) {
    const normalized = exercises
        .map(item => normalizeExercise({
        id: item.exercise?.id != null
            ? String(item.exercise.id)
            : undefined,
        databaseId: item.exercise?.id != null
            ? String(item.exercise.id)
            : null,
        name: item.exercise?.name ??
            t("exercise.fallback"),
        exercise: item.exercise,
        sets: item.sets,
        reps: item.reps,
        duration_sec: item.duration_sec ??
            null,
        load: item.load,
        weight: item.load,
        rpe: item.rpe ?? null,
        set_entries: item.set_entries ?? null,
        done: item.done,
        completed: item.done,
        fromPlan: item.fromPlan
    }))
        .filter((item) => item !== null);
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
        localStorage.setItem(STORAGE_DATE_KEY, getTodayKey());
    }
    catch {
        return;
    }
}
export function getDailySessionId() {
    try {
        if (localStorage.getItem(STORAGE_DATE_KEY) !== getTodayKey()) {
            return null;
        }
        return localStorage.getItem(STORAGE_SESSION_KEY);
    }
    catch {
        return null;
    }
}
export function persistSessionId(sessionId) {
    try {
        localStorage.setItem(STORAGE_SESSION_KEY, String(sessionId));
        localStorage.setItem(STORAGE_DATE_KEY, getTodayKey());
    }
    catch {
        return;
    }
}
export function initDailyState() {
    const saved = getDailyExercises();
    trainingStore.sessionId =
        getDailySessionId();
    trainingStore.workout =
        saved.map(item => {
            // Items saved before measurement types existed carry a stale
            // exercise object; refresh it from the catalog so duration
            // exercises get seconds instead of a leftover reps value.
            const catalogExercise = trainingStore.exercises.find(exercise => String(exercise.id) ===
                String(item.exercise?.id));
            const exercise = catalogExercise
                ? {
                    ...item.exercise,
                    ...catalogExercise
                }
                : item.exercise;
            const defaults = defaultPrescription(exercise);
            const duration = isDurationExercise(exercise);
            return {
                exercise,
                sets: item.sets,
                reps: duration
                    ? null
                    : item.reps ??
                        defaults.reps,
                duration_sec: duration
                    ? item.duration_sec ??
                        defaults.duration_sec
                    : null,
                load: item.load,
                rpe: item.rpe,
                set_entries: item.set_entries ?? undefined,
                done: item.done ||
                    item.completed,
                fromPlan: item.fromPlan
            };
        });
}
