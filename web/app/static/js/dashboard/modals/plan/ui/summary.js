import { dom } from "../dom.js";
import { DAYS } from "../constants.js";
import { state } from "../state.js";

export function updateSummary() {
    const exercises = state.days[state.currentDay] ?? [];
    const sets = exercises.reduce((sum, item) => sum + Number(item.sets || 0), 0);

    if (dom.summaryCount) dom.summaryCount.textContent = `${exercises.length} вправ`;
    if (dom.summarySets) dom.summarySets.textContent = `${sets} підходів`;

    DAYS.forEach(day => {
        const badge = dom.days?.querySelector(`[data-day-badge="${day.key}"]`);
        const count = state.days[day.key]?.length ?? 0;

        if (!badge) return;

        badge.textContent = count || "";
        badge.classList.toggle("visible", count > 0);
    });
}
