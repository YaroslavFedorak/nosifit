import type {
    PlanExercise
} from "../../api.js";

import {
    state
} from "../state.js";

export function updateSummary(
    items?: PlanExercise[]
): void {
    const list =
        items ??
        state.days[
            state.currentDay
        ] ??
        [];

    const count =
        list.length;

    const sets =
        list.reduce(
            (total, item) =>
                total +
                (item.sets || 0),
            0
        );

    const countElement =
        document.getElementById(
            "tr-plan-summary-count"
        );

    const setsElement =
        document.getElementById(
            "tr-plan-summary-sets"
        );

    if (countElement) {
        countElement.textContent =
            `${count} вправ`;
    }

    if (setsElement) {
        setsElement.textContent =
            `${sets} підходів`;
    }

    updateBadges();
}

export function updateBadges(): void {
    Object.keys(
        state.days
    ).forEach(day => {
        const badge =
            document.querySelector<HTMLElement>(
                `[data-day-badge="${day}"]`
            );

        if (!badge) {
            return;
        }

        const count =
            state.days[
                day as keyof typeof state.days
            ]?.length || 0;

        if (count > 0) {
            badge.textContent =
                String(count);

            badge.classList.add(
                "visible"
            );
        } else {
            badge.textContent = "";

            badge.classList.remove(
                "visible"
            );
        }
    });
}