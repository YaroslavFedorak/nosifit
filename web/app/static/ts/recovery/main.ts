import { initRecoveryDashboard } from "./dashboard.js";
import { initHabitModal } from "./modals/habit_modal.js";
import { initSleepModal } from "./modals/sleep_modal.js";
import { initRecoveryHeatmap } from "./heatmap/heatmap.js";
import { initDayDetailsModal } from "./heatmap/day_details/modal.js";
import { ICONS } from "../icons/index.js";

function getUserId(): number | null {
    const app = document.getElementById("recovery-app");

    if (!app) {
        return null;
    }

    const userId = Number(app.dataset.userId);

    if (!Number.isFinite(userId) || userId <= 0) {
        return null;
    }

    return userId;
}

function initHeader(): void {
    const icon = document.getElementById("recovery-header-icon");
    const dateElement = document.getElementById("recovery-header-date");

    if (icon) {
        icon.innerHTML = ICONS.heart_handshake;
    }

    if (dateElement) {
        const date = new Date();

        dateElement.textContent = new Intl.DateTimeFormat("uk-UA", {
            weekday: "long",
            day: "numeric",
            month: "long"
        }).format(date);
    }
}

async function init(): Promise<void> {
    const userId = getUserId();

    if (userId === null) {
        return;
    }

    initHeader();
    initDayDetailsModal();
    initHabitModal(userId);
    initSleepModal(userId);
    initRecoveryHeatmap();

    await initRecoveryDashboard(userId);
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            void init();
        },
        {
            once: true
        }
    );
} else {
    void init();
}