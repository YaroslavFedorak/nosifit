import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { loadTranslations } from "../i18n/index.js";

import {
    renderCurrentDate,
    renderAnalytics,
    renderStrengthTestResults
} from "./dashboard.js";

import { loadPlan } from "./plans.js";

import {
    renderWorkoutList
} from "./workout.js";

import {
    initExercisePicker,
    openExercisePicker
} from "./exercise_picker.js";

import { initSession } from "./session.js";
import { initPlanModal } from "./plan_modal.js";

import {
    renderRecommendations
} from "./recommendations.js";

import { initHeatmap } from "./heatmap.js";

import {
    initStrengthTest
} from "./strength_test.js";

import {
    initDailyState,
    persistWorkout
} from "./state.js";

document.addEventListener(
    "DOMContentLoaded",
    async () => {
        await loadTranslations("training");
        
        renderCurrentDate();

        initHeatmap();

        await Promise.all([
            loadPlan(),

            TrainingAPI.getExercises()
                .then(data => {
                    trainingStore.exercises =
                        Array.isArray(data)
                            ? data
                            : Array.isArray(
                                data.items
                            )
                                ? data.items
                                : [];
                })
                .catch(() => {
                    trainingStore.exercises =
                        [];
                }),

            TrainingAPI.getAnalytics()
                .then(data => {
                    renderAnalytics(data);

                    renderStrengthTestResults(
                        data.raw_performance ??
                        data.performance_raw ??
                        null
                    );
                })
                .catch(() => {
                    return;
                }),

            TrainingAPI.getRecommendations()
                .then(data => {
                    trainingStore.recommendations =
                        data;

                    renderRecommendations(
                        data
                    );
                })
                .catch(() => {
                    trainingStore.recommendations =
                        null;
                })
        ]);

        initDailyState();

        const addExercise =
            document.getElementById(
                "tr-add-exercise"
            );

        if (addExercise) {
            addExercise.onclick = () => {
                openExercisePicker(
                    exercise => {
                        const exists =
                            trainingStore.workout.some(
                                item =>
                                    String(
                                        item.exercise?.id
                                    ) ===
                                    String(
                                        exercise.id
                                    )
                            );

                        if (exists) {
                            return;
                        }

                        trainingStore.workout.push({
                            exercise,
                            sets: 3,
                            reps: "8-12",
                            load: 0,
                            done: false,
                            fromPlan: false
                        });

                        persistWorkout(
                            trainingStore.workout
                        );

                        renderWorkoutList();

                        window.dispatchEvent(
                            new CustomEvent(
                                "training:workout-updated"
                            )
                        );
                    }
                );
            };
        }

        initSession();
        initExercisePicker();
        initPlanModal();
        renderWorkoutList();
        initStrengthTest();
    }
);