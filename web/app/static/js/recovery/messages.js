import { translate } from "../i18n/loader.js";
export const RECOVERY_MESSAGES = {
    get loading() {
        return translate("recovery", "loading");
    },
    get error() {
        return translate("recovery", "error");
    },
    sleep: {
        get empty() {
            return translate("recovery", "sleep.empty");
        },
        get title() {
            return translate("recovery", "sleep.title");
        },
        get scoreLabel() {
            return translate("recovery", "sleep.scoreLabel");
        }
    },
    habits: {
        get empty() {
            return translate("recovery", "habits.empty");
        },
        get title() {
            return translate("recovery", "habits.title");
        },
        get scoreLabel() {
            return translate("recovery", "habits.scoreLabel");
        }
    },
    score: {
        get empty() {
            return translate("recovery", "score.empty");
        },
        get title() {
            return translate("recovery", "score.title");
        },
        get sleepLabel() {
            return translate("recovery", "score.labels.sleep");
        },
        get habitsLabel() {
            return translate("recovery", "score.labels.habits");
        },
        get trainingLabel() {
            return translate("recovery", "score.labels.training");
        },
        get energyLabel() {
            return translate("recovery", "score.labels.energy");
        }
    },
    heatmap: {
        get empty() {
            return translate("recovery", "heatmap.empty");
        },
        get title() {
            return translate("recovery", "heatmap.title");
        },
        get daysLabel() {
            return translate("recovery", "heatmap.daysLabel");
        }
    },
    recommendations: {
        get empty() {
            return translate("recovery", "recommendations.empty");
        },
        get title() {
            return translate("recovery", "recommendations.title");
        }
    }
};
