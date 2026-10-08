import { RecoveryAPI } from "./api.js";
import { renderSleepWidget } from "./sleep.js";
import { renderHabitsWidget } from "./habits.js";
import { renderHeatmapWidget } from "./heatmap/heatmap.js";
import { renderRecommendationsWidget } from "./recommendations.js";
import { renderScoreWidget } from "./score.js";
const state = {
    snapshot: null,
    habits: [],
    heatmap: null,
    recommendations: null,
    firstLoad: true
};
function getUserId() {
    const app = document.getElementById("recovery-app");
    if (!app) {
        return null;
    }
    const userId = Number(app.dataset.userId);
    return Number.isFinite(userId) &&
        userId > 0
        ? userId
        : null;
}
function renderLoading() {
    renderSleepWidget(null, {
        loading: true
    });
    renderHabitsWidget(null, {
        loading: true
    });
    renderScoreWidget(null, {
        loading: true
    });
    renderHeatmapWidget(null, {
        loading: true
    });
    renderRecommendationsWidget(null, {
        loading: true
    });
}
function renderAll() {
    renderSleepWidget(state.snapshot);
    renderHabitsWidget(state.habits);
    renderScoreWidget(state.snapshot);
    renderHeatmapWidget(state.heatmap);
    renderRecommendationsWidget(state.recommendations);
}
export async function refreshRecoveryDashboard(userId) {
    const resolvedUserId = userId ?? getUserId();
    if (resolvedUserId === null) {
        return;
    }
    if (state.firstLoad) {
        renderLoading();
    }
    const [snapshotResult, habitsResult, heatmapResult, recommendationsResult] = await Promise.allSettled([
        RecoveryAPI.getSnapshot(resolvedUserId),
        RecoveryAPI.getHabits(resolvedUserId),
        RecoveryAPI.getHeatmap(resolvedUserId, new Date().getFullYear()),
        RecoveryAPI.getRecommendations(resolvedUserId)
    ]);
    state.snapshot =
        snapshotResult.status === "fulfilled"
            ? snapshotResult.value
            : null;
    state.habits =
        habitsResult.status === "fulfilled"
            ? habitsResult.value
            : [];
    state.heatmap =
        heatmapResult.status === "fulfilled"
            ? heatmapResult.value
            : null;
    state.recommendations =
        recommendationsResult.status === "fulfilled"
            ? recommendationsResult.value
            : null;
    state.firstLoad =
        false;
    renderAll();
}
export async function initRecoveryDashboard(userId) {
    await refreshRecoveryDashboard(userId);
}
export function destroyRecoveryDashboard() {
    state.snapshot =
        null;
    state.habits =
        [];
    state.heatmap =
        null;
    state.recommendations =
        null;
    state.firstLoad =
        true;
}
