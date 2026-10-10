import { dashboard_t, getLocale } from "../../../i18n/index.js";
import { RECOVERY_ICONS } from "../../../icons/recovery.js";
import { formatDashboardDate } from "../../utils/date.js";
function formatDuration(minutes) {
    if (minutes == null ||
        minutes <= 0) {
        return "—";
    }
    const hours = Math.floor(minutes / 60);
    const remaining = minutes % 60;
    if (remaining === 0) {
        return dashboard_t("recovery.sleep.durationHours", {
            hours
        });
    }
    return dashboard_t("recovery.sleep.durationHoursMinutes", {
        hours,
        minutes: remaining
    });
}
function formatTime(value) {
    if (!value) {
        return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "—";
    }
    return date.toLocaleTimeString(getLocale(), {
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
    // A day snapshot exists even without logged sleep (score 0); showing
    // "quality 0/100" then would be a made-up number.
    if (!snapshot || !snapshot.sleep_duration_minutes) {
        duration.textContent =
            "—";
        range.textContent =
            "—";
        quality.textContent =
            dashboard_t("recovery.sleep.noData");
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
            dashboard_t("recovery.sleep.periodUnavailable");
    }
    const score = snapshot.sleep_score;
    if (score != null) {
        quality.textContent =
            dashboard_t("recovery.sleep.quality", {
                score
            });
    }
    else {
        quality.textContent =
            dashboard_t("recovery.sleep.qualityUnavailable");
    }
    if (snapshot.date) {
        meta.textContent =
            formatDashboardDate(snapshot.date);
    }
    else {
        meta.textContent =
            "";
    }
}
