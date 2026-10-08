import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { loadTranslations } from "../i18n/index.js";

import {
    renderCurrentDate
} from "./dashboard.js";

import {
    renderWeeklySets
} from "./weekly_sets.js";

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
    initDailyState,
    persistWorkout
} from "./state.js";

import {
    defaultPrescription
} from "./measurement.js";
import {
    initServerSync
} from "./server_sync.js";

document.addEventListener(
    "DOMContentLoaded",
    async () => {
        await Promise.all([
            loadTranslations("training"),
            loadTranslations("exercises")
        ]);

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
                    renderWeeklySets(
                        data.weekly_sets
                    );
                })
                .catch(() => {
                    renderWeeklySets(null);
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
        initServerSync();

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

                        const prescription =
                            defaultPrescription(
                                exercise
                            );

                        trainingStore.workout.push({
                            exercise,
                            sets: prescription.sets,
                            reps: prescription.reps,
                            duration_sec: prescription.duration_sec,
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
    }
);