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
    return "▰".repeat(blocks) + "▱".repeat(MINI_BAR_SEGMENTS - blocks);
}

export function formatDateShort(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("uk-UA", { day: "numeric", month: "short" });
}

export function formatDateLong(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("uk-UA", { day: "numeric", month: "long", year: "numeric" });
}

export function formatSleep(minutes) {
    if (minutes == null) return null;
    const total = Number(minutes);
    if (Number.isNaN(total) || total < 0) return null;
    const h = Math.floor(total / 60);
    const m = String(total % 60).padStart(2, "0");
    return `${h} год ${m} хв`;
}

export function formatTooltipDayHTML(data) {
    const date = formatDateShort(data.date);
    const score = formatScore(data.recovery_score);
    return `
        <div class="tt-date">${date}</div>
        <div class="tt-line">Відновлення: ${score}</div>
    `;
}
