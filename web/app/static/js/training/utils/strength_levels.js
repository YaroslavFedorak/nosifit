import { t } from "../../i18n/index.js";
const LEVELS = {
    pushups: [
        {
            max: 10,
            labelKey: "strengthLevels.low"
        },
        {
            max: 20,
            labelKey: "strengthLevels.medium"
        },
        {
            max: 35,
            labelKey: "strengthLevels.good"
        },
        {
            max: Infinity,
            labelKey: "strengthLevels.excellent"
        }
    ],
    squats: [
        {
            max: 20,
            labelKey: "strengthLevels.low"
        },
        {
            max: 40,
            labelKey: "strengthLevels.medium"
        },
        {
            max: 70,
            labelKey: "strengthLevels.good"
        },
        {
            max: Infinity,
            labelKey: "strengthLevels.excellent"
        }
    ],
    situps: [
        {
            max: 15,
            labelKey: "strengthLevels.low"
        },
        {
            max: 30,
            labelKey: "strengthLevels.medium"
        },
        {
            max: 50,
            labelKey: "strengthLevels.good"
        },
        {
            max: Infinity,
            labelKey: "strengthLevels.excellent"
        }
    ]
};
const MAX_PROGRESS = {
    pushups: 40,
    squats: 80,
    situps: 60
};
export function getLevel(type, value) {
    const ranges = LEVELS[type] || [];
    for (const range of ranges) {
        if (value <=
            range.max) {
            return t(range.labelKey);
        }
    }
    return t("strengthLevels.low");
}
export function getProgress(type, value) {
    const max = MAX_PROGRESS[type] || 40;
    return Math.min(100, Math.floor((value / max) * 100));
}
