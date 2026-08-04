import { trainingStore } from "./store.js";
import { ICONS } from "../icons/index.js";

export function renderWorkoutList() {
    const box = document.getElementById("tr-workout-exercise-list");
    if (!box) return;
    box.innerHTML = "";

    const sorted = [...trainingStore.workout].sort((a, b) => {
        if (a.done && !b.done) return 1;
        if (!a.done && b.done) return -1;
        return 0;
    });

    if (!sorted.length) {
        const empty = document.createElement("div");
        empty.className = "tr-session-empty";
        empty.textContent = "Додати тренування+";
        empty.onclick = () => {
            const btn = document.getElementById("tr-add-exercise");
            if (btn) btn.click();
        };
        box.appendChild(empty);
        return;
    }

    sorted.forEach(item => {
        const row = document.createElement("div");
        row.className = "tr-session-ex-row";
        if (item.done) row.classList.add("tr-ex-done");

        const nameWrap = document.createElement("div");
        nameWrap.className = "tr-session-ex-name-wrap";

        const name = document.createElement("div");
        name.className = "tr-session-ex-name";
        name.textContent = item.exercise.name;

        nameWrap.appendChild(name);

        if (item.fromPlan) {
            const planIcon = document.createElement("span");
            planIcon.className = "tr-session-ex-plan-icon";
            planIcon.innerHTML = ICONS.plan;
            nameWrap.appendChild(planIcon);
        }

        const makeInlineBlock = (labelText, initialValue, onChange, isRange = false, disabled = false) => {
            const wrap = document.createElement("div");
            wrap.className = "tr-input-inline";

            const input = document.createElement("input");
            input.className = "tr-input-field";
            input.value = initialValue;
            input.disabled = disabled;
            input.oninput = () => {
                if (!input.disabled) onChange(input.value);
            };

            const arrows = document.createElement("div");
            arrows.className = "tr-input-arrows";

            const up = document.createElement("div");
            up.className = "tr-arrow tr-arrow-up";
            up.onclick = () => {
                if (input.disabled) return;
                const val = input.value;
                if (isRange) {
                    const [a, b] = val.split("-").map(Number);
                    const nv = `${a + 1}-${b + 1}`;
                    input.value = nv;
                    onChange(nv);
                } else {
                    const nv = (parseInt(val, 10) || 0) + 1;
                    input.value = nv;
                    onChange(nv);
                }
            };

            const down = document.createElement("div");
            down.className = "tr-arrow tr-arrow-down";
            down.onclick = () => {
                if (input.disabled) return;
                const val = input.value;
                if (isRange) {
                    const [a, b] = val.split("-").map(Number);
                    const na = Math.max(1, a - 1);
                    const nb = Math.max(na, b - 1);
                    const nv = `${na}-${nb}`;
                    input.value = nv;
                    onChange(nv);
                } else {
                    const nv = Math.max(0, (parseInt(val, 10) || 0) - 1);
                    input.value = nv;
                    onChange(nv);
                }
            };

            const label = document.createElement("span");
            label.className = "tr-input-inline-label";
            label.textContent = labelText;

            arrows.appendChild(up);
            arrows.appendChild(down);
            wrap.appendChild(input);
            wrap.appendChild(arrows);
            wrap.appendChild(label);

            if (disabled) wrap.classList.add("tr-input-inline-disabled");

            return wrap;
        };

        const disabled = item.done;

        const setsBlock = makeInlineBlock("підх.", item.sets, v => item.sets = parseInt(v, 10) || 0, false, disabled);
        const repsBlock = makeInlineBlock("повт.", item.reps, v => item.reps = v, true, disabled);
        const loadBlock = makeInlineBlock("кг", item.load, v => item.load = parseFloat(v) || 0, false, disabled);

        const check = document.createElement("div");
        check.className = "tr-ex-check";
        if (item.done) check.classList.add("checked");
        check.onclick = () => {
            item.done = !item.done;
            renderWorkoutList();
        };

        row.appendChild(nameWrap);
        row.appendChild(repsBlock);
        row.appendChild(setsBlock);
        row.appendChild(loadBlock);
        row.appendChild(check);

        box.appendChild(row);
    });
}
