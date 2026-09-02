import { state } from "../state.js";
import { dom } from "../dom.js";
import { createExerciseCard } from "./exerciseCard.js";
import { updateSummary } from "./summary.js";

export function renderExercises(openPicker) {
    dom.container.innerHTML = "";
    const list = state.days[state.currentDay] ?? [];

    if (!list.length) {
        dom.emptyState.classList.add("visible");
        updateSummary(list);
        return;
    }

    dom.emptyState.classList.remove("visible");

    const rerender = () => renderExercises(openPicker);

    list.forEach((ex, index) => {
        dom.container.appendChild(
            createExerciseCard(ex, index, list, rerender, openPicker)
        );
    });

    updateSummary(list);
}
