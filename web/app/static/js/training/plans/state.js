import { DAYS } from "./constants.js";

export const state = {
    days: {},
    currentDay: "mon"
};

export function normalize(days) {
    const normalized = {};

    DAYS.forEach(d => {
        const arr = Array.isArray(days[d.key]) ? days[d.key] : [];

        normalized[d.key] = arr.map(item => ({
            exercise: item.exercise,
            sets: Number(item.sets) || 0,
            reps: item.reps || "8–12",
            load: Number(item.load) || 0
        }));
    });

    return normalized;
}

export function initState(reset = false) {
    const plan = window.trainingStore.plan;

    if (!reset && plan && plan.days) {
        state.days = normalize(plan.days);
        state.currentDay = "mon";
        return;
    }

    state.days = {};
    DAYS.forEach(d => {
        state.days[d.key] = [];
    });

    state.currentDay = "mon";
}
