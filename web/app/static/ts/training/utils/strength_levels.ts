type StrengthType =
    | "pushups"
    | "squats"
    | "situps";

type LevelRange = {
    max: number;
    label: string;
};

const LEVELS: Record<
    StrengthType,
    LevelRange[]
> = {
    pushups: [
        { max: 10, label: "Низький" },
        { max: 20, label: "Середній" },
        { max: 35, label: "Добрий" },
        { max: Infinity, label: "Відмінний" }
    ],

    squats: [
        { max: 20, label: "Низький" },
        { max: 40, label: "Середній" },
        { max: 70, label: "Добрий" },
        { max: Infinity, label: "Відмінний" }
    ],

    situps: [
        { max: 15, label: "Низький" },
        { max: 30, label: "Середній" },
        { max: 50, label: "Добрий" },
        { max: Infinity, label: "Відмінний" }
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

    for (const range of ranges) {
        if (value <= range.max) {
            return range.label;
        }
    }

    return "Низький";
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