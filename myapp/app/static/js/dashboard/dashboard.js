import * as api from "./api.js";
import * as state from "./state.js";
import { renderRecommendations } from "./widgets/recommendations.js";
import { renderHeatmap } from "./heatmap/render.js";

function bindOverview(overview) {
    const daily = document.getElementById("daily-score");
    const training = document.getElementById("training-load");
    const recovery = document.getElementById("recovery-score");
    const sleep = document.getElementById("sleep-score");

    if (daily) {
        const v = overview && overview.daily_score != null ? String(overview.daily_score) : "—";
        const elv = daily.querySelector(".dashboard-metric-value");
        if (elv) elv.textContent = v;
    }
    if (training) {
        const v =
            overview &&
            overview.training &&
            overview.training.score != null
                ? String(overview.training.score)
                : "—";
        const elv = training.querySelector(".dashboard-metric-value");
        if (elv) elv.textContent = v;
    }
    if (recovery) {
        const v =
            overview &&
            overview.recovery &&
            overview.recovery.score != null
                ? String(overview.recovery.score)
                : "—";
        const elv = recovery.querySelector(".dashboard-metric-value");
        if (elv) elv.textContent = v;
    }
    if (sleep) {
        const v =
            overview &&
            overview.recovery &&
            overview.recovery.sleep_hours != null
                ? String(overview.recovery.sleep_hours)
                : "—";
        const elv = sleep.querySelector(".dashboard-metric-value");
        if (elv) elv.textContent = v;
    }
}

function bindHeatmap(data) {
    const container = document.getElementById("dashboard-heatmap");
    if (!container) return;
    renderHeatmap(container, data);
}

function bindRecommendations(rec) {
    const container = document.getElementById("recommendations-list");
    if (!container) return;
    renderRecommendations(container, rec);
}

async function loadAll() {
    const [overview, heatmap, recommendation] = await Promise.all([
        api.fetchOverview(),
        api.fetchHeatmap(),
        api.fetchRecommendation()
    ]);
    state.setOverview(overview);
    state.setHeatmap(heatmap);
    state.setRecommendations(recommendation);
}

function init() {
    state.subscribe("overview", bindOverview);
    state.subscribe("heatmap", bindHeatmap);
    state.subscribe("recommendations", bindRecommendations);

    loadAll();

    window.addEventListener("dashboard:refresh", () => {
        loadAll();
    });
}

document.addEventListener("DOMContentLoaded", init);
