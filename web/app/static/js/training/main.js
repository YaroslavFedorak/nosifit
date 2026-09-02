import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { renderCurrentDate, renderAnalytics, renderStrengthTestResults } from "./dashboard.js";
import { loadPlan } from "./plans.js";
import { renderWorkoutList } from "./workout.js";
import { initExercisePicker, openExercisePicker } from "./exercise_picker.js";
import { initSession } from "./session.js";
import { initPlanModal } from "./plan_modal.js";
import { renderRecommendations } from "./recommendations.js";
import { initHeatmap } from "./heatmap.js";
import { initStrengthTest, injectIcons, setupArrows } from "./strength_test.js";

document.addEventListener("DOMContentLoaded", async () => {
    renderCurrentDate();

    await Promise.all([
        loadPlan(),

        TrainingAPI.getExercises()
            .then(data => {
                trainingStore.exercises = Array.isArray(data?.items)
                    ? data.items
                    : Array.isArray(data)
                        ? data
                        : [];
            })
            .catch(() => {
                trainingStore.exercises = [];
            }),

        TrainingAPI.getAnalytics()
            .then(data => {
                renderAnalytics(data);
                renderStrengthTestResults(
                    data?.raw_performance ??
                    data?.performance_raw ??
                    data?.performance ??
                    null
                );
            })
            .catch(() => {}),

        TrainingAPI.getRecommendations()
            .then(data => {
                trainingStore.recommendations = data;
                renderRecommendations(data);
            })
            .catch(() => {
                trainingStore.recommendations = null;
            })
    ]);

    const addExercise = document.getElementById("tr-add-exercise");
    if (addExercise) {
        addExercise.onclick = () => {
            openExercisePicker(ex => {
                trainingStore.workout.push({
                    exercise: ex,
                    sets: 3,
                    reps: "8-12",
                    load: 0,
                    done: false,
                    fromPlan: false
                });
                renderWorkoutList();
            });
        };
    }

    initSession();
    initExercisePicker();
    initPlanModal();
    renderWorkoutList();
    initHeatmap();
    initStrengthTest();
    injectIcons();
    setupArrows();
});
