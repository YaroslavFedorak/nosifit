import { trainingStore } from "../store.js";
import { DAYS } from "./constants.js";
export const state = {
    days: {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    },
    currentDay: "mon"
};
export function normalize(days) {
    const normalized = {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    };
    if (!days ||
        typeof days !== "object") {
        return normalized;
    }
    DAYS.forEach(day => {
        const value = days[day.key];
        if (!Array.isArray(value)) {
            return;
        }
        normalized[day.key] = value
            .filter(item => item &&
            typeof item === "object" &&
            "exercise" in item)
            .map(item => ({
            exercise: item.exercise,
            sets: Number(item.sets) || 0,
            reps: item.reps || "8–12",
            load: Number(item.load) || 0
        }));
    });
    return normalized;
}
function createEmptyDays() {
    return {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    };
}
export function initState(reset = false) {
    if (!reset &&
        trainingStore.plan?.days) {
        state.days = normalize(trainingStore.plan.days);
        state.currentDay = "mon";
        return;
    }
    if (!reset) {
        return;
    }
    state.days = createEmptyDays();
    state.currentDay = "mon";
}
export function getCurrentDayExercises() {
    return state.days[state.currentDay] ?? [];
}
