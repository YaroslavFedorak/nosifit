import { TrainingAPI } from "./widgets/training/api.js";
import { RecoveryAPI } from "./modals/recovery/api.js";
const API_BASE = "/api/dashboard";
async function jsonFetch(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            Accept: "application/json",
            ...(options.body
                ? {
                    "Content-Type": "application/json"
                }
                : {}),
            ...(options.headers || {})
        },
        cache: "no-store",
        ...options
    });
    let data = null;
    try {
        data =
            await response.json();
    }
    catch (_) {
        data = null;
    }
    if (!response.ok) {
        console.error(`Dashboard API error: ${response.status} ${url}`, data);
        throw new Error(data?.message ||
            data?.error ||
            `HTTP ${response.status}`);
    }
    return data;
}
export function getToday() {
    return jsonFetch(`${API_BASE}/today`);
}
export function getHeatmap() {
    return jsonFetch(`${API_BASE}/heatmap`);
}
export function getDay(date) {
    return jsonFetch(`${API_BASE}/day/${encodeURIComponent(date)}`);
}
export function getRecommendation() {
    return jsonFetch(`${API_BASE}/recommendation`);
}
export function getExercises(params = {}) {
    return TrainingAPI.getExercises(params);
}
export function getRecoveryHabits() {
    return RecoveryAPI.getHabitsList();
}
export function getUserRecoveryHabits(userId) {
    return RecoveryAPI.getUserHabits(userId);
}
export function addRecoveryHabit(userId, habitId) {
    return RecoveryAPI.addHabit(userId, habitId);
}
export function addSleep(userId, sleepStart, sleepEnd) {
    return RecoveryAPI.addSleep(userId, sleepStart, sleepEnd);
}
export const DashboardAPI = {
    getToday,
    getHeatmap,
    getDay,
    getRecommendation,
    getExercises,
    getRecoveryHabits,
    getUserRecoveryHabits,
    addRecoveryHabit,
    addSleep
};
