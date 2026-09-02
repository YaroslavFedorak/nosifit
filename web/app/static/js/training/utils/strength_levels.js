const LEVELS = {
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

const MAX_PROGRESS = {
    pushups: 40,
    squats: 80,
    situps: 60
};

export function getLevel(type, value) {
    const ranges = LEVELS[type] || [];
    for (const r of ranges) {
        if (value <= r.max) return r.label;
    }
    return "Низький";
}

export function getProgress(type, value) {
    const max = MAX_PROGRESS[type] || 40;
    return Math.min(100, Math.floor((value / max) * 100));
}
