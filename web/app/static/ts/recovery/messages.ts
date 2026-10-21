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