import { dashboard_t } from "../../../../i18n/index.js";
import { dom } from "../dom.js";
import { getPlanDays } from "../constants.js";
import { state } from "../state.js";
export function updateSummary() {
    const exercises = state.days[state.currentDay] ?? [];
    const sets = exercises.reduce((sum, item) => sum +
        Number(item.sets || 0), 0);
    if (dom.summaryCount) {
        dom.summaryCount.textContent =
            dashboard_t("plan.summary.exercises", {
                count: exercises.length
            });
    }
    if (dom.summarySets) {
        dom.summarySets.textContent =
            dashboard_t("plan.summary.sets", {
                count: sets
            });
    }
    const days = getPlanDays();
    days.forEach(day => {
        const badge = dom.days?.querySelector(`[data-day-badge="${day.key}"]`);
        const count = state.days[day.key]?.length ?? 0;
        if (!badge) {
            return;
        }
        badge.textContent =
            count
                ? String(count)
                : "";
        badge.classList.toggle("visible", count > 0);
    });
}
