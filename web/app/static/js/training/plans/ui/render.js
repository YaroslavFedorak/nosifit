import { createExerciseCard } from "./exerciseCard.js";
import { updateSummary } from "./summary.js";
import { state } from "../state.js";
export function renderExercises(openPicker) {
    const container = document.getElementById("tr-plan-exercises");
    const emptyState = document.getElementById("tr-plan-empty");
    if (!container ||
        !emptyState) {
        return;
    }
    const list = state.days[state.currentDay];
    container.innerHTML = "";
    if (!list.length) {
        container.classList.add("hidden");
        emptyState.classList.remove("hidden");
        updateSummary();
        return;
    }
    container.classList.remove("hidden");
    emptyState.classList.add("hidden");
    const rerender = () => {
        renderExercises(openPicker);
    };
    list.forEach((exercise, index) => {
        const card = createExerciseCard(exercise, index, list, rerender, openPicker);
        container.appendChild(card);
    });
    updateSummary();
}
