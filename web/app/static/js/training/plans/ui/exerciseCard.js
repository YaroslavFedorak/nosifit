import { createCounterField, createRepsField } from "./counters.js";
import { enableDrag } from "../interactions/dragdrop.js";
import { ICONS } from "../../../icons/index.js";
export function createExerciseCard(exercise, index, list, rerender, openPicker) {
    const card = document.createElement("div");
    card.className =
        "tr-plan-card";
    card.innerHTML = `
        <div class="tr-plan-card-header">
            <div class="tr-plan-card-header-left">
                <div class="tr-plan-card-strip"></div>
                <button class="tr-plan-ex-name">
                    ${exercise.exercise.name}
                </button>
            </div>

            <div class="tr-plan-card-header-right">
                <button class="tr-plan-card-drag">
                    ${ICONS.grip}
                </button>

                <button class="tr-plan-card-delete">
                    ${ICONS.delete}
                </button>
            </div>
        </div>

        <div class="tr-plan-card-body"></div>
    `;
    const nameButton = card.querySelector(".tr-plan-ex-name");
    const deleteButton = card.querySelector(".tr-plan-card-delete");
    const body = card.querySelector(".tr-plan-card-body");
    if (!nameButton ||
        !deleteButton ||
        !body) {
        return card;
    }
    const reps = createRepsField(exercise.reps, value => {
        exercise.reps =
            value;
    });
    const sets = createCounterField("Підходи", ICONS.exercise, exercise.sets, value => {
        exercise.sets =
            value;
    });
    const load = createCounterField("Вага (кг)", ICONS.exercise, exercise.load, value => {
        exercise.load =
            value;
    });
    body.appendChild(reps);
    body.appendChild(sets);
    body.appendChild(load);
    nameButton.onclick = () => {
        openPicker(selectedExercise => {
            exercise.exercise =
                selectedExercise;
            rerender();
        });
    };
    deleteButton.onclick = () => {
        list.splice(index, 1);
        rerender();
    };
    enableDrag(card, index, list, rerender);
    return card;
}
