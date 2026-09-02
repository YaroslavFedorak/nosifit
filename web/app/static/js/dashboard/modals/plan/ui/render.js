import { dom } from "../dom.js";
import {
    getCurrentExercises,
    moveExercise,
    removeExercise,
    replaceExercise
} from "../state.js";
import { createExerciseCard } from "./exerciseCard.js";
import { updateSummary } from "./summary.js";

export function renderExercises(openExercisePicker) {
    const exercises = getCurrentExercises();

    if (!dom.exercises || !dom.emptyState) return;

    dom.exercises.innerHTML = "";
    dom.emptyState.classList.toggle("visible", exercises.length === 0);

    exercises.forEach((item, index) => {
        const card = createExerciseCard(item, index, {
            replace: selectedIndex => {
                openExercisePicker(exercise => {
                    replaceExercise(selectedIndex, exercise);
                    renderExercises(openExercisePicker);
                });
            },
            remove: selectedIndex => {
                removeExercise(selectedIndex);
                renderExercises(openExercisePicker);
            },
            move: (fromIndex, toIndex) => {
                moveExercise(fromIndex, toIndex);
                renderExercises(openExercisePicker);
            }
        });

        dom.exercises.appendChild(card);
    });

    updateSummary();
}
