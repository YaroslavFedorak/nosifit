import { RECOVERY_MESSAGES } from "./messages.js";
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
    userId: null,
    errors: {
        snapshot: null,
        heatmap: null,
        recommendations: null
    }
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

    if (opts.error) {
        grid.innerHTML = "";
        grid.textContent = RECOVERY_MESSAGES.error;
        return;
    }

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
    renderSleepWidget(state.snapshot, { error: state.errors.snapshot });
    renderHabitsWidget(state.snapshot, { error: state.errors.snapshot });
    renderScoreWidget(state.snapshot, { error: state.errors.snapshot });
    renderHeatmapWidget(state.heatmap, { error: state.errors.heatmap });
    renderRecommendationsWidget(state.recommendations, { error: state.errors.recommendations });
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

    if (snapshotRes.status === "fulfilled") {
        state.snapshot = snapshotRes.value;
        state.errors.snapshot = null;
    } else {
        state.snapshot = null;
        state.errors.snapshot = snapshotRes.reason?.message || "Failed to load snapshot";
    }

    if (heatmapRes.status === "fulfilled") {
        state.heatmap = heatmapRes.value;
        state.errors.heatmap = null;
    } else {
        state.heatmap = null;
        state.errors.heatmap = heatmapRes.reason?.message || "Failed to load heatmap";
    }

    if (recommendationsRes.status === "fulfilled") {
        state.recommendations = recommendationsRes.value;
        state.errors.recommendations = null;
    } else {
        state.recommendations = null;
        state.errors.recommendations = recommendationsRes.reason?.message || "Failed to load recommendations";
    }

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
    state.errors = { snapshot: null, heatmap: null, recommendations: null };
}
