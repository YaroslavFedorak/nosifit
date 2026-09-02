import { createCounterField, createRepsField } from "./counters.js";
import { enableDrag } from "../interactions/dragdrop.js";
import { ICONS } from "../../../icons/index.js";

export function createExerciseCard(ex, index, list, rerender, openPicker) {
    const card = document.createElement("div");
    card.className = "tr-plan-card";

    card.innerHTML = `
        <div class="tr-plan-card-header">
            <div class="tr-plan-card-header-left">
                <div class="tr-plan-card-strip"></div>
                <button class="tr-plan-ex-name">${ex.exercise.name}</button>
            </div>
            <div class="tr-plan-card-header-right">
                <button class="tr-plan-card-drag">${ICONS.grip}</button>
                <button class="tr-plan-card-delete">${ICONS.delete}</button>
            </div>
        </div>
        <div class="tr-plan-card-body"></div>
    `;

    const nameBtn = card.querySelector(".tr-plan-ex-name");
    const deleteBtn = card.querySelector(".tr-plan-card-delete");
    const body = card.querySelector(".tr-plan-card-body");

    const reps = createRepsField(ex.reps, v => ex.reps = v);
    const sets = createCounterField("Підходи", ICONS.exercise, ex.sets, v => ex.sets = v);
    const load = createCounterField("Вага (кг)", ICONS.exercise, ex.load, v => ex.load = v);

    body.appendChild(reps);
    body.appendChild(sets);
    body.appendChild(load);

    nameBtn.onclick = () => openPicker(ex, rerender);

    deleteBtn.onclick = () => {
        list.splice(index, 1);
        rerender();
    };

    enableDrag(card, index, list, rerender);

    return card;
}
