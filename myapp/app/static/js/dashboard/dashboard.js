import * as api from "./api.js";
import * as state from "./state.js";

import {
    renderRecommendations
} from "./widgets/recommendations.js";

import {
    renderSession
} from "./widgets/session.js";

import * as trainingEditor
    from "./widgets/training/index.js";

import {
    renderHeatmap
} from "./heatmap/render.js";

import {
    openExerciseModal,
    initExerciseModal
} from "./modals/exercise.js";

import {
    openPlanModal,
    initPlanModal
} from "./modals/plan.js";


function setMetricValue(id, value) {
    const container =
        document.getElementById(id);

    if (!container) {
        return;
    }

    const element =
        container.querySelector(
            ".dashboard-metric-value"
        );

    if (!element) {
        return;
    }

    element.textContent =
        value == null ||
        value === ""
            ? "—"
            : String(value);
}


function bindOverview(overview) {
    if (!overview) {
        setMetricValue(
            "daily-score",
            "—"
        );

        setMetricValue(
            "training-load",
            "—"
        );

        setMetricValue(
            "recovery-score",
            "—"
        );

        setMetricValue(
            "sleep-score",
            "—"
        );

        bindRecoverySummary({});
        bindNutritionSummary({});

        return;
    }

    setMetricValue(
        "daily-score",
        overview.daily_score
    );

    setMetricValue(
        "training-load",
        overview.training?.score
    );

    setMetricValue(
        "recovery-score",
        overview.recovery?.score
    );

    const sleep =
        overview.recovery?.sleep_hours ??
        overview.sleep_hours;

    setMetricValue(
        "sleep-score",
        sleep != null
            ? `${sleep} год`
            : "—"
    );

    bindRecoverySummary(overview);
    bindNutritionSummary(overview);
}


function bindRecoverySummary(overview) {
    const recoveryScore =
        document.getElementById(
            "dashboard-recovery-score"
        );

    const sleep =
        document.getElementById(
            "dashboard-sleep"
        );

    const habits =
        document.getElementById(
            "dashboard-habits"
        );

    if (recoveryScore) {
        const value =
            overview.recovery?.score;

        recoveryScore.textContent =
            value != null
                ? `${value}`
                : "—";
    }

    if (sleep) {
        const value =
            overview.recovery?.sleep_hours;

        sleep.textContent =
            value != null
                ? `${value} год`
                : "—";
    }

    if (habits) {
        const value =
            overview.recovery?.habits_score ??
            overview.recovery?.habits;

        habits.textContent =
            value != null
                ? `${value}`
                : "—";
    }
}


function bindNutritionSummary(overview) {
    const nutrition =
        overview?.nutrition;

    if (!nutrition) {
        return;
    }

    const calories =
        document.getElementById(
            "dashboard-calories"
        );

    const protein =
        document.getElementById(
            "dashboard-protein"
        );

    const water =
        document.getElementById(
            "dashboard-water"
        );

    if (calories) {
        calories.textContent =
            nutrition.calories != null
                ? `${Math.round(
                    Number(
                        nutrition.calories
                    )
                )} ккал`
                : "—";
    }

    if (protein) {
        protein.textContent =
            nutrition.protein != null
                ? `${Math.round(
                    Number(
                        nutrition.protein
                    )
                )} г`
                : "—";
    }

    if (water) {
        water.textContent =
            nutrition.water != null
                ? `${Math.round(
                    Number(
                        nutrition.water
                    )
                )} мл`
                : "—";
    }
}


function bindHeatmap(data) {
    const container =
        document.getElementById(
            "dashboard-heatmap"
        );

    if (!container) {
        return;
    }

    renderHeatmap(
        container,
        data
    );
}


function bindRecommendations(
    recommendation
) {
    const container =
        document.getElementById(
            "recommendations-list"
        );

    if (!container) {
        return;
    }

    renderRecommendations(
        container,
        recommendation
    );
}


function bindTraining(data) {
    const container =
        document.getElementById(
            "dashboard-session-summary"
        );

    if (!container) {
        return;
    }

    renderSession(
        container,
        data
    );
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

    state.setOverview(
        overview
    );

    state.setHeatmap(
        heatmap
    );

    state.setRecommendations(
        recommendation
    );

    state.setTraining(
        training
    );
}


function getTrainingPlan(training) {
    if (!training) {
        return null;
    }

    return (
        training.plan ??
        training.training_plan ??
        training.program ??
        training
    );
}


function handleExerciseSelected(
    exercise
) {
    trainingEditor.addExercise(
        exercise
    );
}


function handleStartPlan(plan) {
    window.dispatchEvent(
        new CustomEvent(
            "dashboard:start-plan",
            {
                detail: plan
            }
        )
    );
}


async function handleSaveWorkout() {
    const completed =
        trainingEditor
            .getCompletedExercises();

    const titleInput =
        document.getElementById(
            "dashboard-workout-title"
        );

    const title =
        titleInput?.value?.trim() ||
        "Тренування";

    if (!completed.length) {
        return;
    }

    const fatigueBefore =
        document.body.dataset.fatigueBefore
        || null;

    const sessionResponse =
        await api.startTrainingSession(
            fatigueBefore
        );

    if (!sessionResponse) {
        return;
    }

    const session =
        sessionResponse.session;

    if (!session?.id) {
        return;
    }

    for (const exercise of completed) {
        const added =
            await api.addExerciseToSession(
                session.id,
                exercise.id
            );

        if (!added) {
            continue;
        }

        await api.updateSessionExercise(
            session.id,
            exercise.id,
            {
                sets_done:
                    exercise.sets,
                reps_done:
                    exercise.reps,
                load_done:
                    exercise.weight,
                rpe:
                    exercise.rpe || null
            }
        );
    }

    const fatigueAfter =
        document.body.dataset.fatigueAfter
        || null;

    const finished =
        await api.finishTrainingSession(
            session.id,
            fatigueAfter
        );

    if (!finished) {
        return;
    }

    trainingEditor.clear();

    if (titleInput) {
        titleInput.value = "";
    }

    await loadAll();

    window.dispatchEvent(
        new CustomEvent(
            "dashboard:training-saved",
            {
                detail: finished
            }
        )
    );
}


function bindNavigation() {
    const trainingButton =
        document.getElementById(
            "dashboard-open-training"
        );

    if (!trainingButton) {
        return;
    }

    trainingButton.addEventListener(
        "click",
        () => {
            const currentState =
                state.getState();

            const plan =
                getTrainingPlan(
                    currentState.training
                );

            openPlanModal(
                plan,
                handleStartPlan
            );
        }
    );
}


function bindWorkoutActions() {
    const addExerciseButton =
        document.getElementById(
            "dashboard-add-exercise"
        );

    const saveButton =
        document.getElementById(
            "dashboard-save-workout"
        );

    if (addExerciseButton) {
        addExerciseButton.addEventListener(
            "click",
            () => {
                openExerciseModal(
                    handleExerciseSelected
                );
            }
        );
    }

    if (saveButton) {
        saveButton.addEventListener(
            "click",
            handleSaveWorkout
        );
    }
}


function initModals() {
    initExerciseModal();
    initPlanModal();
}


async function init() {
    state.subscribe(
        "overview",
        bindOverview
    );

    state.subscribe(
        "heatmap",
        bindHeatmap
    );

    state.subscribe(
        "recommendations",
        bindRecommendations
    );

    state.subscribe(
        "training",
        bindTraining
    );

    trainingEditor.init();

    initModals();

    bindNavigation();
    bindWorkoutActions();

    await loadAll();

    window.addEventListener(
        "dashboard:refresh",
        loadAll
    );
}


document.addEventListener(
    "DOMContentLoaded",
    init
);