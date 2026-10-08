import { defaultPrescription, isDurationExercise } from "../../../training/measurement.js";
const DEFAULT_DAY = "mon";
export const state = {
    planId: null,
    days: {},
    currentDay: DEFAULT_DAY
};
function toNonNegativeNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number)
        ? Math.max(0, number)
        : fallback;
}
function normalizeExercise(exercise = {}) {
    const source = exercise.exercise ??
        exercise;
    const defaults = defaultPrescription(source);
    const duration = isDurationExercise(source);
    return {
        exercise: source,
        sets: toNonNegativeNumber(exercise.sets ??
            source.sets, defaults.sets),
        reps: duration
            ? null
            : String(exercise.reps ??
                source.reps ??
                defaults.reps),
        duration_sec: duration
            ? toNonNegativeNumber(exercise.duration_sec ??
                source.duration_sec, defaults.duration_sec ?? 0) || defaults.duration_sec
            : null,
        load: toNonNegativeNumber(exercise.load ??
            exercise.weight, 0)
    };
}
export function normalizeDays(days = {}) {
    const dayKeys = [
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun"
    ];
    return dayKeys.reduce((normalized, dayKey) => {
        const rawDay = days?.[dayKey];
        const exercises = Array.isArray(rawDay)
            ? rawDay
            : Array.isArray(rawDay?.exercises)
                ? rawDay.exercises
                : [];
        normalized[dayKey] =
            exercises.map(normalizeExercise);
        return normalized;
    }, {});
}
export function setPlan(plan = null) {
    state.planId =
        plan?.id ?? null;
    state.days =
        normalizeDays(plan?.days);
    state.currentDay =
        DEFAULT_DAY;
}
export function addExercise(exercise) {
    if (!state.days[state.currentDay]) {
        state.days[state.currentDay] = [];
    }
    state.days[state.currentDay].push(normalizeExercise({
        exercise
    }));
}
export function replaceExercise(index, exercise) {
    const exercises = state.days[state.currentDay];
    const current = exercises?.[index];
    if (!current) {
        return;
    }
    exercises[index] =
        normalizeExercise({
            exercise,
            sets: current.sets,
            load: current.load
        });
}
export function removeExercise(index) {
    const exercises = state.days[state.currentDay];
    if (!exercises) {
        return;
    }
    exercises.splice(index, 1);
}
export function moveExercise(fromIndex, toIndex) {
    const exercises = state.days[state.currentDay];
    if (!exercises) {
        return;
    }
    const [exercise] = exercises.splice(fromIndex, 1);
    if (exercise) {
        exercises.splice(toIndex, 0, exercise);
    }
}
export function getCurrentExercises() {
    return (state.days[state.currentDay] || []);
}
