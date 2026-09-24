import {
    t
} from "../../i18n/index.js";

type StrengthType =
    | "pushups"
    | "squats"
    | "situps";

type LevelRange = {
    max: number;
    labelKey: string;
};

const LEVELS: Record<
    StrengthType,
    LevelRange[]
> = {
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

const MAX_PROGRESS: Record<
    StrengthType,
    number
> = {
    pushups: 40,
    squats: 80,
    situps: 60
};

export function getLevel(
    type: StrengthType,
    value: number
): string {
    const ranges =
        LEVELS[type] || [];

    for (
        const range of ranges
    ) {
        if (
            value <=
            range.max
        ) {
            return t(
                range.labelKey
            );
        }
    }

    return t(
        "strengthLevels.low"
    );
}

export function getProgress(
    type: StrengthType,
    value: number
): number {
    const max =
        MAX_PROGRESS[type] || 40;

    return Math.min(
        100,
        Math.floor(
            (value / max) * 100
        )
    );
}