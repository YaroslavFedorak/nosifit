import { RECOVERY_ICONS } from "../../../icons/recovery.js";
function formatDuration(minutes) {
    if (minutes == null ||
        minutes <= 0) {
        return "—";
    }
    const hours = Math.floor(minutes / 60);
    const remaining = minutes % 60;
    if (remaining === 0) {
        return `${hours} год`;
    }
    return `${hours} год ${remaining} хв`;
}
function formatTime(value) {
    if (!value) {
        return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "—";
    }
    return date.toLocaleTimeString("uk-UA", {
        hour: "2-digit",
        minute: "2-digit"
    });
}
function renderSleepIcon() {
    const icon = document.getElementById("dashboard-sleep-icon");
    if (!icon) {
        return;
    }
    icon.innerHTML =
        RECOVERY_ICONS.moon;
}
export function renderSleepWidget(snapshot) {
    const duration = document.getElementById("dashboard-sleep-duration");
    const range = document.getElementById("dashboard-sleep-range");
    const quality = document.getElementById("dashboard-sleep-quality");
    const meta = document.getElementById("dashboard-sleep-meta");
    if (!duration ||
        !range ||
        !quality ||
        !meta) {
        return;
    }
    renderSleepIcon();
    if (!snapshot) {
        duration.textContent =
            "—";
        range.textContent =
            "—";
        quality.textContent =
            "Дані відсутні";
        meta.textContent =
            "";
        return;
    }
    duration.textContent =
        formatDuration(snapshot.sleep_duration_minutes);
    if (snapshot.sleep_start &&
        snapshot.sleep_end) {
        range.textContent =
            `${formatTime(snapshot.sleep_start)} — ${formatTime(snapshot.sleep_end)}`;
    }
    else {
        range.textContent =
            "Період сну не записаний";
    }
    const score = snapshot.sleep_score;
    if (score != null) {
        quality.textContent =
            `Якість ${score}/100`;
    }
    else {
        quality.textContent =
            "Якість не визначена";
    }
    if (snapshot.date) {
        meta.textContent =
            snapshot.date;
    }
    else {
        meta.textContent =
            "";
    }
}
