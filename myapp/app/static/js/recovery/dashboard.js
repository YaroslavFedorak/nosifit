import { RecoveryAPI } from "./api.js";
import { renderSleepWidget } from "./sleep.js";
import { renderHabitsWidget } from "./habits.js";
import { renderRecoveryHeatmap } from "./heatmap/heatmap.js";
import { renderRecommendationsWidget } from "./recommendations.js";
import { renderScoreWidget } from "./score.js";

const CURRENT_YEAR = new Date().getFullYear();

const state = {
    snapshot: null,
    heatmap: null,
    recommendations: null,
    firstLoad: true,
    userId: null
};

function resolveUserId() {
    if (state.userId) return state.userId;
    const root = document.getElementById("recovery-app");
    state.userId = root?.dataset?.userId || null;
    return state.userId;
}

function renderHeatmapWidget(data, opts = {}) {
    const grid = document.getElementById("recovery-heatmap");

    if (opts.loading) {
        if (grid) grid.innerHTML = "<div class='rc-loading'>Завантаження…</div>";
        return;
    }

    if (!grid) return;

    const days = Array.isArray(data?.days) ? data.days : [];
    renderRecoveryHeatmap(days);
}

function renderLoading() {
    renderSleepWidget(null, { loading: true });
    renderHabitsWidget(null, { loading: true });
    renderScoreWidget(null, { loading: true });
    renderHeatmapWidget(null, { loading: true });
    renderRecommendationsWidget(null, { loading: true });
}

function renderAll() {
    renderSleepWidget(state.snapshot);
    renderHabitsWidget(state.snapshot);
    renderScoreWidget(state.snapshot);
    renderHeatmapWidget(state.heatmap);
    renderRecommendationsWidget(state.recommendations);
}

export async function refreshRecoveryDashboard() {
    const userId = resolveUserId();
    if (!userId) return;

    if (state.firstLoad) {
        renderLoading();
    }

    const [snapshotRes, heatmapRes, recommendationsRes] =
        await Promise.allSettled([
            RecoveryAPI.getSnapshot(userId),
            RecoveryAPI.getHeatmap(userId, CURRENT_YEAR),
            RecoveryAPI.getRecommendations(userId)
        ]);

    state.snapshot = snapshotRes.status === "fulfilled" ? snapshotRes.value : null;
    state.heatmap = heatmapRes.status === "fulfilled" ? heatmapRes.value : null;
    state.recommendations =
        recommendationsRes.status === "fulfilled" ? recommendationsRes.value : null;

    state.firstLoad = false;

    renderAll();
}

export async function initRecoveryDashboard() {
    resolveUserId();
    await refreshRecoveryDashboard();
}

export function destroyRecoveryDashboard() {
    state.snapshot = null;
    state.heatmap = null;
    state.recommendations = null;
    state.firstLoad = true;
}
