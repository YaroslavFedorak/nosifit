import { state } from "../state.js";

export function updateSummary() {
    const day = state.currentDay;
    const items = state.days[day] || [];

    const count = items.length;
    const sets = items.reduce((acc, item) => acc + (item.sets || 0), 0);

    document.getElementById("tr-plan-summary-count").textContent = `${count} вправ`;
    document.getElementById("tr-plan-summary-sets").textContent = `${sets} підходів`;

    updateBadges();
}

export function updateBadges() {
    Object.keys(state.days).forEach(day => {
        const badge = document.querySelector(`[data-day-badge="${day}"]`);
        if (!badge) return;

        const count = state.days[day]?.length || 0;

        if (count > 0) {
            badge.textContent = count;
            badge.classList.add("visible");
        } else {
            badge.textContent = "";
            badge.classList.remove("visible");
        }
    });
}
