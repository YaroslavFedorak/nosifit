import { DAYS } from "./constants.js";

export const state = {
    planId: null,
    days: {},
    currentDay: DAYS[0].key
};

function toNonNegativeNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(0, number) : fallback;
}

function normalizeExercise(exercise = {}) {
    return {
        exercise: exercise.exercise ?? exercise,
        sets: toNonNegativeNumber(exercise.sets, 3),
        reps: String(exercise.reps ?? "8-12"),
        load: toNonNegativeNumber(exercise.load ?? exercise.weight, 0)
    };
}

export function normalizeDays(days = {}) {
    return DAYS.reduce((normalized, day) => {
        const rawDay = days[day.key];
        const exercises = Array.isArray(rawDay)
            ? rawDay
            : Array.isArray(rawDay?.exercises)
                ? rawDay.exercises
                : [];
        normalized[day.key] = exercises.map(normalizeExercise);
        return normalized;
    }, {});
}

export function setPlan(plan = null) {
    state.planId = plan?.id ?? null;
    state.days = normalizeDays(plan?.days);
    state.currentDay = DAYS[0].key;
}

export function addExercise(exercise) {
    state.days[state.currentDay].push(normalizeExercise({ exercise }));
}

export function replaceExercise(index, exercise) {
    const exercises = state.days[state.currentDay];
    const current = exercises[index];

    if (!current) return;

    exercises[index] = {
        ...current,
        exercise
    };
}

export function removeExercise(index) {
    state.days[state.currentDay].splice(index, 1);
}

export function moveExercise(fromIndex, toIndex) {
    const exercises = state.days[state.currentDay];
    const [exercise] = exercises.splice(fromIndex, 1);

    if (exercise) exercises.splice(toIndex, 0, exercise);
}

export function getCurrentExercises() {
    return state.days[state.currentDay];
}
