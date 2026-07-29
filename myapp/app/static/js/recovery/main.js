import { initRecoveryDashboard } from "./dashboard.js";
import { initSleepModal } from "./modals/sleep_modal.js";
import { initHabitModal } from "./modals/habit_modal.js";
import { initRecoveryHeatmap } from "./heatmap/heatmap.js";
import { ICONS } from "../icons/icons.js";

document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("recovery-app");
    if (!root) return;

    const rawUserId = root.dataset.userId;
    const userId = Number(rawUserId);
    if (!rawUserId || Number.isNaN(userId)) return;

    const iconBox = document.getElementById("recovery-header-icon");
    if (iconBox) iconBox.innerHTML = ICONS.bed_single;

    const dateEl = document.getElementById("recovery-header-date");
    if (dateEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString("uk-UA", {
            day: "numeric",
            month: "long",
            year: "numeric"
        });
    }

    initSleepModal(userId);
    initHabitModal(userId);
    initRecoveryHeatmap();
    initRecoveryDashboard();
});
