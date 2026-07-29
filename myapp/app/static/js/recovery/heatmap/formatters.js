const MINI_BAR_SEGMENTS = 5;
export const LOW_THRESHOLD = 40;
export const HIGH_THRESHOLD = 70;

export function normalizeScore(value) {
    if (typeof value !== "number" || Number.isNaN(value)) return 0;
    return Math.max(0, Math.min(value, 100));
}

export function formatScore(value) {
    return value == null ? "—" : normalizeScore(value);
}

export function getLevel(value) {
    const v = normalizeScore(value);
    if (v < LOW_THRESHOLD) return "low";
    if (v < HIGH_THRESHOLD) return "medium";
    return "high";
}

export function formatMiniBar(value) {
    const v = normalizeScore(value);
    const blocks = Math.round(v / (100 / MINI_BAR_SEGMENTS));
    const filled = "▰".repeat(blocks);
    const empty = "▱".repeat(MINI_BAR_SEGMENTS - blocks);
    return filled + empty;
}

export function formatDateShort(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "short"
    });
}

export function formatDateLong(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric"
    });
}

export function formatSleep(minutes) {
    if (minutes == null) return null;
    const total = Number(minutes);
    if (Number.isNaN(total) || total < 0) return null;
    const hours = Math.floor(total / 60);
    const mins = String(total % 60).padStart(2, "0");
    return `${hours} год ${mins} хв`;
}

export function formatTooltipDay(dateStr, score) {
    const date = formatDateShort(dateStr);
    const v = normalizeScore(score);
    return `${date} · Відновлення ${v}`;
}
