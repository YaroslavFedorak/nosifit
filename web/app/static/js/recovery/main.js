import { initRecoveryDashboard } from "./dashboard.js";
import { initHabitModal } from "./modals/habit_modal.js";
import { initSleepModal } from "./modals/sleep_modal.js";
import { initRecoveryHeatmap } from "./heatmap/heatmap.js";
import { initDayDetailsModal } from "./heatmap/day_details/modal.js";
import { ICONS } from "../icons/index.js";
import { loadTranslations, getLocale } from "../i18n/index.js";
function getUserId() {
    const app = document.getElementById("recovery-app");
    if (!app) {
        return null;
    }
    const userId = Number(app.dataset.userId);
    if (!Number.isFinite(userId) ||
        userId <= 0) {
        return null;
    }
    return userId;
}
function initHeader() {
    const icon = document.getElementById("recovery-header-icon");
    const dateElement = document.getElementById("recovery-header-date");
    if (icon) {
        icon.innerHTML =
            ICONS.heart_handshake;
    }
    if (dateElement) {
        const date = new Date();
        const localeMap = {
            uk: "uk-UA",
            en: "en-US",
            pl: "pl-PL",
            ru: "ru-RU"
        };
        dateElement.textContent =
            new Intl.DateTimeFormat(localeMap[getLocale()] ?? "uk-UA", {
                weekday: "long",
                day: "numeric",
                month: "long"
            }).format(date);
    }
}
async function init() {
    const userId = getUserId();
    if (userId === null) {
        return;
    }
    await loadTranslations("recovery");
    initHeader();
    initDayDetailsModal();
    initHabitModal(userId);
    initSleepModal(userId);
    initRecoveryHeatmap();
    await initRecoveryDashboard(userId);
}
if (document.readyState ===
    "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        void init();
    }, {
        once: true
    });
}
else {
    void init();
}
