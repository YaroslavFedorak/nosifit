import { el } from "../../utils/dom.js";
import * as state from "./state.js";

function createInput(
    exercise: any,
    field: string,
    value: any,
    label: string
): HTMLElement {
    const input =
        el("input", {
            class: "db-input-field",
            type: "text",
            value: value ?? "",
            disabled: exercise.completed
        }) as HTMLInputElement;

    input.setAttribute(
        "data-exercise-id",
        exercise.id
    );

    input.setAttribute(
        "data-field",
        field
    );

    const arrows =
        el(
            "div",
            {
                class: "db-input-arrows"
            },
            [
                el("div", {
                    class:
                        "db-arrow db-arrow-up"
                }),

                el("div", {
                    class:
                        "db-arrow db-arrow-down"
                })
            ]
        ) as HTMLElement;

    const arrowUp =
        arrows.children[0] as HTMLElement;

    const arrowDown =
        arrows.children[1] as HTMLElement;

    arrowUp.setAttribute(
        "data-exercise-id",
        exercise.id
    );

    arrowUp.setAttribute(
        "data-field",
        field
    );

    arrowUp.setAttribute(
        "data-action",
        "arrow-up"
    );

    arrowDown.setAttribute(
        "data-exercise-id",
        exercise.id
    );

    arrowDown.setAttribute(
        "data-field",
        field
    );

    arrowDown.setAttribute(
        "data-action",
        "arrow-down"
    );

    return el(
        "div",
        {
            class: "db-input-inline"
        },
        [
            input,

            el("span", {
                class:
                    "db-input-inline-label",
                text: label
            }),

            arrows
        ]
    ) as HTMLElement;
}

function createCheckbox(
    exercise: any
): HTMLButtonElement {
    const button =
        el("button", {
            class:
                `db-ex-check ${
                    exercise.completed
                        ? "checked"
                        : ""
                }`,

            type: "button",

            ariaLabel:
                exercise.completed
                    ? "Виконано"
                    : "Позначити виконаною"
        }) as HTMLButtonElement;

    button.setAttribute(
        "data-exercise-id",
        exercise.id
    );

    button.setAttribute(
        "data-action",
        "toggle"
    );

    return button;
}

function createExerciseRow(
    exercise: any
): HTMLElement {
    const row =
        el("div", {
            class:
                `db-session-ex-row ${
                    exercise.completed
                        ? "db-ex-done"
                        : ""
                }`
        }) as HTMLElement;

    row.setAttribute(
        "data-exercise-id",
        exercise.id
    );

    row.appendChild(
        el(
            "div",
            {
                class:
                    "db-session-ex-name-wrap"
            },
            [
                el("div", {
                    class:
                        "db-session-ex-name",

                    text:
                        exercise.name
                })
            ]
        ) as HTMLElement
    );

    row.appendChild(
        createInput(
            exercise,
            "sets",
            exercise.sets,
            "під"
        )
    );

    row.appendChild(
        createInput(
            exercise,
            "reps",
            exercise.reps,
            "пов"
        )
    );

    row.appendChild(
        createInput(
            exercise,
            "weight",
            exercise.weight,
            "кг"
        )
    );

    row.appendChild(
        createCheckbox(exercise)
    );

    return row;
}

function createEmptyState(): HTMLElement {
    return el("div", {
        class: "db-session-empty",
        text:
            "Додайте вправи до тренування"
    }) as HTMLElement;
}

export function render(
    container: HTMLElement | null
): void {
    if (!container) {
        return;
    }

    container.innerHTML = "";

    const exercises =
        state.getExercises();

    if (!exercises.length) {
        container.appendChild(
            createEmptyState()
        );

        return;
    }

    const active =
        exercises.filter(
            exercise =>
                !exercise.completed
        );

    const completed =
        exercises.filter(
            exercise =>
                exercise.completed
        );

    const fragment =
        document.createDocumentFragment();

    active.forEach(
        exercise => {
            fragment.appendChild(
                createExerciseRow(
                    exercise
                )
            );
        }
    );

    completed.forEach(
        exercise => {
            fragment.appendChild(
                createExerciseRow(
                    exercise
                )
            );
        }
    );

    container.appendChild(fragment);
}