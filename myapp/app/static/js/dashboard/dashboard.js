import * as api from "./api.js";
import * as state from "./state.js";
import { renderRecommendations } from "./widgets/recommendations.js";
import * as trainingEditor from "./widgets/training/index.js";
import { saveWorkout } from "./widgets/training/controller.js";
import { renderHeatmap } from "./heatmap/render.js";
import { openExerciseModal, initExerciseModal } from "./modals/exercise.js";
import { openPlanModal, initPlanModal } from "./modals/plan.js";

function setMetricValue(id, value) {
    const container = document.getElementById(id);
    if (!container) return;
    const element = container.querySelector(".dashboard-metric-value");
    if (!element) return;
    element.textContent = value == null || value === "" ? "—" : String(value);
}

function bindOverview(overview) {
    if (!overview) {
        setMetricValue("daily-score", "—");
        setMetricValue("training-load", "—");
        setMetricValue("recovery-score", "—");
        setMetricValue("sleep-score", "—");
        return;
    }
    setMetricValue("daily-score", overview.daily_score);
    setMetricValue("training-load", overview.training?.score ?? overview.training?.load);
    setMetricValue("recovery-score", overview.recovery?.score);
    const sleep = overview.recovery?.sleep_hours ?? overview.sleep_hours;
    setMetricValue("sleep-score", sleep != null ? `${sleep} год` : "—");
    bindRecoverySummary(overview);
    bindNutritionSummary(overview);
}

function bindRecoverySummary(overview) {
    const recoveryScore = document.getElementById("dashboard-recovery-score");
    const sleep = document.getElementById("dashboard-sleep");
    const habits = document.getElementById("dashboard-habits");
    if (recoveryScore) {
        const value = overview?.recovery?.score;
        recoveryScore.textContent = value != null ? String(value) : "—";
    }
    if (sleep) {
        const value = overview?.recovery?.sleep_hours;
        sleep.textContent = value != null ? `${value} год` : "—";
    }
    if (habits) {
        const value = overview?.recovery?.habits_score ?? overview?.recovery?.habits;
        habits.textContent = value != null ? String(value) : "—";
    }
}

function bindNutritionSummary(overview) {
    const nutrition = overview?.nutrition;
    const calories = document.getElementById("dashboard-calories");
    const protein = document.getElementById("dashboard-protein");
    const water = document.getElementById("dashboard-water");
    if (!nutrition) {
        if (calories) calories.textContent = "—";
        if (protein) protein.textContent = "—";
        if (water) water.textContent = "—";
        return;
    }
    if (calories) {
        const value = Number(nutrition.calories);
        calories.textContent = Number.isFinite(value) ? `${Math.round(value)} ккал` : "—";
    }
    if (protein) {
        const value = Number(nutrition.protein);
        protein.textContent = Number.isFinite(value) ? `${Math.round(value)} г` : "—";
    }
    if (water) {
        const value = Number(nutrition.water);
        water.textContent = Number.isFinite(value) ? `${Math.round(value)} мл` : "—";
    }
}

function bindHeatmap(data) {
    const container = document.getElementById("dashboard-heatmap");
    if (!container) return;
    renderHeatmap(container, data);
}

function bindRecommendations(recommendations) {
    const container = document.getElementById("recommendations-list");
    if (!container) return;
    renderRecommendations(container, recommendations);
}

function getTrainingPlan(training) {
    if (!training) return null;
    return training.plan ?? training.training_plan ?? training.program ?? null;
}

function loadPersistedExercises() {
    try {
        const raw = window.localStorage.getItem("dashboard_training_exercises");
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
        return [];
    }
}

function restoreTodayExercises(overview) {
    const training = overview?.training;
    let exercises = [];

    if (training) {
        const fromOverview = training.exercises ?? training.completed_exercises ?? [];
        if (Array.isArray(fromOverview) && fromOverview.length) {
            exercises = fromOverview;
        }
    }

    if (!exercises.length) {
        exercises = loadPersistedExercises();
    }

    if (!Array.isArray(exercises) || !exercises.length) return;

    trainingEditor.replaceExercises(exercises);
}

function handleExerciseSelected(exercise) {
    if (!exercise) return;
    const added = trainingEditor.addExercise(exercise);
    if (!added) {
        console.error("Failed to add exercise:", exercise);
    }
}

function handleStartPlan(plan) {
    if (!plan || !Array.isArray(plan.exercises)) return;
    trainingEditor.replaceExercises(plan.exercises);
    const titleInput = document.getElementById("dashboard-workout-title");
    if (titleInput) {
        titleInput.value = plan.title ?? plan.name ?? "Тренування";
    }
}

async function handleSaveWorkout() {
    try {
        const exercises = trainingEditor.getCompletedExercises();
        const finished = await saveWorkout({
            exercises,
            onSuccess: async result => {
                await loadAll();
                window.dispatchEvent(new CustomEvent("dashboard:training-saved", { detail: result }));
            }
        });
        if (finished) {
            alert("Тренування успішно збережено!");
        }
    } catch (error) {
        console.error("Failed to save workout:", error);
        alert(error.message || "Не вдалося зберегти тренування.");
    }
}

async function loadAll() {
    try {
        const [overview, heatmap, recommendations] = await Promise.all([
            api.getToday(),
            api.getHeatmap(),
            api.getRecommendation()
        ]);

        restoreTodayExercises(overview);

        state.setOverview(overview);
        state.setHeatmap(heatmap);
        state.setRecommendations(recommendations);
    } catch (error) {
        console.error("Failed to load dashboard:", error);
    }
}

function bindNavigation() {
    const trainingButton = document.getElementById("dashboard-open-training");
    if (!trainingButton) return;
    trainingButton.addEventListener("click", () => {
        const currentState = state.getState();
        const plan = getTrainingPlan(currentState.training);
        openPlanModal(plan, handleStartPlan);
    });
}

function bindWorkoutActions() {
    const addExerciseButton = document.getElementById("dashboard-add-exercise");
    const saveButton = document.getElementById("dashboard-save-workout");
    if (addExerciseButton) {
        addExerciseButton.addEventListener("click", () => {
            openExerciseModal(handleExerciseSelected);
        });
    }
    if (saveButton) {
        saveButton.addEventListener("click", handleSaveWorkout);
    }
}

function initModals() {
    initExerciseModal();
    initPlanModal();
}

function initSubscriptions() {
    state.subscribe("overview", bindOverview);
    state.subscribe("heatmap", bindHeatmap);
    state.subscribe("recommendations", bindRecommendations);
}

async function init() {
    initSubscriptions();
    trainingEditor.init();
    initModals();
    bindNavigation();
    bindWorkoutActions();
    await loadAll();
    window.addEventListener("dashboard:refresh", loadAll);
}

document.addEventListener("DOMContentLoaded", init);
