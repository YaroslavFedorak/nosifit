import * as api from "./api.js";
import * as state from "./state.js";
import { renderRecommendations } from "./widgets/recommendations.js";
import { renderSession } from "./widgets/session.js";
import { renderHeatmap } from "./heatmap/render.js";

function bindOverview(overview) {
    const daily = document.getElementById("daily-score");
    const training = document.getElementById("training-load");
    const recovery = document.getElementById("recovery-score");
    const sleep = document.getElementById("sleep-score");

    if (daily) {
        const value =
            overview && overview.daily_score != null
                ? String(overview.daily_score)
                : "—";

        const element = daily.querySelector(".dashboard-metric-value");

        if (element) {
            element.textContent = value;
        }
    }

    if (training) {
        const value =
            overview &&
            overview.training &&
            overview.training.score != null
                ? String(overview.training.score)
                : "—";

        const element = training.querySelector(".dashboard-metric-value");

        if (element) {
            element.textContent = value;
        }
    }

    if (recovery) {
        const value =
            overview &&
            overview.recovery &&
            overview.recovery.score != null
                ? String(overview.recovery.score)
                : "—";

        const element = recovery.querySelector(".dashboard-metric-value");

        if (element) {
            element.textContent = value;
        }
    }

    if (sleep) {
        const value =
            overview &&
            overview.recovery &&
            overview.recovery.sleep_hours != null
                ? String(overview.recovery.sleep_hours)
                : "—";

        const element = sleep.querySelector(".dashboard-metric-value");

        if (element) {
            element.textContent = value;
        }
    }
}

function bindHeatmap(data) {
    const container = document.getElementById("dashboard-heatmap");

    if (!container) {
        return;
    }

    renderHeatmap(container, data);
}

function bindRecommendations(recommendation) {
    const container = document.getElementById("recommendations-list");

    if (!container) {
        return;
    }

    renderRecommendations(container, recommendation);
}

function bindTraining(data) {
    const container = document.getElementById("dashboard-training-session");

    if (!container) {
        return;
    }

    renderSession(container, data);
}

async function loadAll() {
    const [
        overview,
        heatmap,
        recommendation,
        training
    ] = await Promise.all([
        api.fetchOverview(),
        api.fetchHeatmap(),
        api.fetchRecommendation(),
        api.fetchTraining()
    ]);

    state.setOverview(overview);
    state.setHeatmap(heatmap);
    state.setRecommendations(recommendation);
    state.setTraining(training);
}

async function init() {
    state.subscribe("overview", bindOverview);
    state.subscribe("heatmap", bindHeatmap);
    state.subscribe("recommendations", bindRecommendations);
    state.subscribe("training", bindTraining);

    await loadAll();

    window.addEventListener("dashboard:refresh", () => {
        loadAll();
    });
}

document.addEventListener("DOMContentLoaded", init);