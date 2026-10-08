import {
    translate
} from "../i18n/loader.js";

export const RECOVERY_MESSAGES = {
    get loading(): string {
        return translate(
            "recovery",
            "loading"
        );
    },

    get error(): string {
        return translate(
            "recovery",
            "error"
        );
    },

    sleep: {
        get empty(): string {
            return translate(
                "recovery",
                "sleep.empty"
            );
        },

        get title(): string {
            return translate(
                "recovery",
                "sleep.title"
            );
        },

        get scoreLabel(): string {
            return translate(
                "recovery",
                "sleep.scoreLabel"
            );
        }
    },

    habits: {
        get empty(): string {
            return translate(
                "recovery",
                "habits.empty"
            );
        },

        get title(): string {
            return translate(
                "recovery",
                "habits.title"
            );
        },

        get scoreLabel(): string {
            return translate(
                "recovery",
                "habits.scoreLabel"
            );
        }
    },

    score: {
        get empty(): string {
            return translate(
                "recovery",
                "score.empty"
            );
        },

        get title(): string {
            return translate(
                "recovery",
                "score.title"
            );
        },

        get sleepLabel(): string {
            return translate(
                "recovery",
                "score.labels.sleep"
            );
        },

        get habitsLabel(): string {
            return translate(
                "recovery",
                "score.labels.habits"
            );
        },

        get trainingLabel(): string {
            return translate(
                "recovery",
                "score.labels.training"
            );
        },

        get energyLabel(): string {
            return translate(
                "recovery",
                "score.labels.energy"
            );
        }
    },

    heatmap: {
        get empty(): string {
            return translate(
                "recovery",
                "heatmap.empty"
            );
        },

        get title(): string {
            return translate(
                "recovery",
                "heatmap.title"
            );
        },

        get daysLabel(): string {
            return translate(
                "recovery",
                "heatmap.daysLabel"
            );
        }
    },

    recommendations: {
        get empty(): string {
            return translate(
                "recovery",
                "recommendations.empty"
            );
        },

        get title(): string {
            return translate(
                "recovery",
                "recommendations.title"
            );
        }
    }
} as const;