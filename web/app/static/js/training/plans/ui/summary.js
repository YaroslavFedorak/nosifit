import { state } from "../state.js";
import { t } from "../../../i18n/index.js";
export function updateSummary(items) {
    const list = items ??
        state.days[state.currentDay] ??
        [];
    const count = list.length;
    const sets = list.reduce((total, item) => total +
        (item.sets || 0), 0);
    const countElement = document.getElementById("tr-plan-summary-count");
    const setsElement = document.getElementById("tr-plan-summary-sets");
    if (countElement) {
        countElement.textContent =
            `${count} ${t("summary.exercises")}`;
    }
    if (setsElement) {
        setsElement.textContent =
            `${sets} ${t("summary.sets")}`;
    }
    updateBadges();
}
export function updateBadges() {
    Object.keys(state.days).forEach(day => {
        const badge = document.querySelector(`[data-day-badge="${day}"]`);
        if (!badge) {
            return;
        }
        const count = state.days[day]?.length || 0;
        if (count > 0) {
            badge.textContent =
                String(count);
            badge.classList.add("visible");
        }
        else {
            badge.textContent =
                "";
            badge.classList.remove("visible");
        }
    });
}
