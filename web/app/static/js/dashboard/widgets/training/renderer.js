import { el } from "../../utils/dom.js";
import * as state from "./state.js";

function createInput(exercise, field, value, label) {
    const input = el("input", {
        class: "db-input-field",
        type: "text",
        value: value ?? "",
        disabled: exercise.completed
    });

    input.setAttribute("data-exercise-id", exercise.id);
    input.setAttribute("data-field", field);

    const arrows = el("div", { class: "db-input-arrows" }, [
        el("div", { class: "db-arrow db-arrow-up" }),
        el("div", { class: "db-arrow db-arrow-down" })
    ]);

    arrows.children[0].setAttribute("data-exercise-id", exercise.id);
    arrows.children[0].setAttribute("data-field", field);
    arrows.children[0].setAttribute("data-action", "arrow-up");

    arrows.children[1].setAttribute("data-exercise-id", exercise.id);
    arrows.children[1].setAttribute("data-field", field);
    arrows.children[1].setAttribute("data-action", "arrow-down");

    return el("div", { class: "db-input-inline" }, [
        input,
        el("span", { class: "db-input-inline-label", text: label }),
        arrows
    ]);
}

function createCheckbox(exercise) {
    const button = el("button", {
        class: `db-ex-check ${exercise.completed ? "checked" : ""}`,
        type: "button",
        ariaLabel: exercise.completed ? "Виконано" : "Позначити виконаною"
    });

    button.setAttribute("data-exercise-id", exercise.id);
    button.setAttribute("data-action", "toggle");

    return button;
}

function createExerciseRow(exercise) {
    const row = el("div", {
        class: `db-session-ex-row ${exercise.completed ? "db-ex-done" : ""}`
    });

    row.setAttribute("data-exercise-id", exercise.id);

    row.appendChild(
        el("div", { class: "db-session-ex-name-wrap" }, [
            el("div", { class: "db-session-ex-name", text: exercise.name })
        ])
    );

    row.appendChild(createInput(exercise, "sets", exercise.sets, "під"));
    row.appendChild(createInput(exercise, "reps", exercise.reps, "пов"));
    row.appendChild(createInput(exercise, "weight", exercise.weight, "кг"));
    row.appendChild(createCheckbox(exercise));

    return row;
}

function createEmptyState() {
    return el("div", { class: "db-session-empty", text: "Додайте вправи до тренування" });
}

export function render(container) {
    if (!container) return;

    container.innerHTML = "";

    const exercises = state.getExercises();

    if (!exercises.length) {
        container.appendChild(createEmptyState());
        return;
    }

    const active = exercises.filter(ex => !ex.completed);
    const completed = exercises.filter(ex => ex.completed);

    const fragment = document.createDocumentFragment();

    active.forEach(exercise => fragment.appendChild(createExerciseRow(exercise)));
    completed.forEach(exercise => fragment.appendChild(createExerciseRow(exercise)));

    container.appendChild(fragment);
}
