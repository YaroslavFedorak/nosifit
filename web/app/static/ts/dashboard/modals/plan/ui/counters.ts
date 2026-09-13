import { ICONS } from "../../../../icons/index.js";
import { PlanExercise } from "../state.js";

function createArrow(
    className: string,
    onClick: () => void
): HTMLDivElement {
    const arrow =
        document.createElement("div");

    arrow.className =
        className;

    arrow.addEventListener(
        "click",
        onClick
    );

    return arrow;
}

function createLabel(
    label: string,
    icon: string
): HTMLDivElement {
    const row =
        document.createElement("div");

    row.className =
        "db-plan-field-label-row";

    row.innerHTML =
        `<span class="db-plan-field-icon">${icon}</span><span class="db-plan-field-label"></span>`;

    const labelElement =
        row.querySelector(
            ".db-plan-field-label"
        );

    if (labelElement) {
        labelElement.textContent =
            label;
    }

    return row;
}

export function createNumberField(
    label: string,
    icon: string,
    value: number,
    onChange: (value: number) => void
): HTMLDivElement {
    const field =
        document.createElement("div");

    field.className =
        "db-plan-field";

    const input =
        document.createElement("input");

    input.type = "text";
    input.inputMode = "numeric";
    input.pattern = "[0-9]*";
    input.value =
        String(value);
    input.className =
        "db-input-field db-plan-counter-input";

    const update = (
        nextValue: string | number
    ): void => {
        const normalized =
            Math.max(
                0,
                Number(nextValue) || 0
            );

        input.value =
            String(normalized);

        onChange(normalized);
    };

    const arrows =
        document.createElement("div");

    arrows.className =
        "db-input-arrows";

    arrows.append(
        createArrow(
            "db-arrow db-arrow-up",
            () =>
                update(
                    Number(
                        input.value
                    ) + 1
                )
        ),
        createArrow(
            "db-arrow db-arrow-down",
            () =>
                update(
                    Number(
                        input.value
                    ) - 1
                )
        )
    );

    const control =
        document.createElement("div");

    control.className =
        "db-input-inline";

    control.append(
        input,
        arrows,
        document.createElement(
            "span"
        )
    );

    input.addEventListener(
        "input",
        () =>
            update(
                input.value
            )
    );

    field.append(
        createLabel(
            label,
            icon
        ),
        control
    );

    return field;
}

function parseRange(
    value: string
): [number, number] {
    const parts =
        String(value)
            .split("-")
            .map(Number);

    return parts.length === 2 &&
        parts.every(
            Number.isFinite
        )
        ? [
            parts[0],
            parts[1]
        ]
        : [8, 12];
}

export function createRepsField(
    value: string,
    onChange: (value: string) => void
): HTMLDivElement {
    const field =
        document.createElement("div");

    field.className =
        "db-plan-field";

    const input =
        document.createElement("input");

    input.type = "text";
    input.value =
        value;
    input.className =
        "db-input-field db-plan-reps-input";

    const update = (
        from: number,
        to: number
    ): void => {
        const next =
            `${from}-${to}`;

        input.value =
            next;

        onChange(next);
    };

    const arrows =
        document.createElement("div");

    arrows.className =
        "db-input-arrows";

    arrows.append(
        createArrow(
            "db-arrow db-arrow-up",
            () => {
                const [
                    from,
                    to
                ] =
                    parseRange(
                        input.value
                    );

                update(
                    from + 1,
                    to + 1
                );
            }
        ),
        createArrow(
            "db-arrow db-arrow-down",
            () => {
                const [
                    from,
                    to
                ] =
                    parseRange(
                        input.value
                    );

                const nextFrom =
                    Math.max(
                        1,
                        from - 1
                    );

                update(
                    nextFrom,
                    Math.max(
                        nextFrom,
                        to - 1
                    )
                );
            }
        )
    );

    const control =
        document.createElement("div");

    control.className =
        "db-input-inline";

    control.append(
        input,
        arrows,
        document.createElement(
            "span"
        )
    );

    input.addEventListener(
        "input",
        () => {
            const [
                from,
                to
            ] =
                parseRange(
                    input.value
                );

            update(
                from,
                to
            );
        }
    );

    field.append(
        createLabel(
            "Повтори",
            ICONS.exercise
        ),
        control
    );

    return field;
}