import { getLocale, recovery_t } from "../../i18n/index.js";
const MINI_BAR_SEGMENTS = 5;
export const LOW_THRESHOLD = 40;
export const HIGH_THRESHOLD = 70;
function parseLocalDate(value) {
    if (!value) {
        return null;
    }
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) {
        const parsed = new Date(value);
        return Number.isNaN(parsed.getTime())
            ? null
            : parsed;
    }
    const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12, 0, 0);
    return Number.isNaN(date.getTime())
        ? null
        : date;
}
export function normalizeScore(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round(numeric)));
}
export function formatScore(value) {
    return value == null
        ? 0
        : normalizeScore(value);
}
export function getLevel(value) {
    const score = normalizeScore(value);
    if (score < LOW_THRESHOLD) {
        return "low";
    }
    if (score < HIGH_THRESHOLD) {
        return "medium";
    }
    return "high";
}
export function formatMiniBar(value) {
    const score = normalizeScore(value);
    const blocks = Math.round(score /
        (100 / MINI_BAR_SEGMENTS));
    return ("▰".repeat(blocks) +
        "▱".repeat(MINI_BAR_SEGMENTS -
            blocks));
}
export function formatDateShort(value) {
    const date = parseLocalDate(value);
    if (!date) {
        return "";
    }
    return date.toLocaleDateString(getLocale(), {
        day: "numeric",
        month: "short"
    });
}
export function formatDateLong(value) {
    const date = parseLocalDate(value);
    if (!date) {
        return "";
    }
    return date.toLocaleDateString(getLocale(), {
        day: "numeric",
        month: "long",
        year: "numeric"
    });
}
export function formatWeekday(value) {
    const date = parseLocalDate(value);
    if (!date) {
        return "";
    }
    return date.toLocaleDateString(getLocale(), {
        weekday: "long"
    });
}
export function formatSleep(minutes) {
    if (minutes == null) {
        return null;
    }
    const total = Number(minutes);
    if (!Number.isFinite(total) ||
        total < 0) {
        return null;
    }
    const rounded = Math.floor(total);
    const hours = Math.floor(rounded / 60);
    const mins = String(rounded % 60).padStart(2, "0");
    return recovery_t("time.sleep", {
        hours,
        minutes: mins
    });
}
export function formatTooltipDayHTML(data) {
    const date = data.date
        ? formatDateShort(data.date)
        : "";
    const score = data.recovery_score == null
        ? 0
        : normalizeScore(data.recovery_score);
    return `
        <div class="tt-single-line">
            <span class="tt-score">${score} ${recovery_t("heatmap.recovery")}</span>
            <span class="tt-date">${date}</span>
        </div>
    `;
}
export function formatDailySummary(data) {
    const parts = [];
    const sessions = data.training?.sessions ??
        0;
    if (sessions > 0) {
        parts.push(recovery_t("day_details.summary.training", {
            count: sessions
        }));
    }
    const sleep = data.sleep?.duration_minutes;
    const sleepText = formatSleep(sleep);
    if (sleepText) {
        parts.push(recovery_t("day_details.summary.sleep", {
            value: sleepText
        }));
    }
    parts.push(recovery_t("day_details.summary.habits", {
        completed: data.habits?.completed ?? 0,
        total: data.habits?.total ?? 0
    }));
    return parts.join(" · ");
}
