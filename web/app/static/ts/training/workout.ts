import { trainingStore } from "./store.js";

import type {
    WorkoutExercise
} from "./api.js";

import {
    persistWorkout
} from "./state.js";

import { ICONS } from "../icons/index.js";

import { t } from "../i18n/index.js";

type InputChangeHandler = (
    value: string | number
) => void;

function makeInlineBlock(
    labelText: string,
    initialValue: string | number | null | undefined,
    onChange: InputChangeHandler,
    isRange = false,
    disabled = false
): HTMLDivElement {
    const wrap =
        document.createElement("div");

    wrap.className =
        "tr-input-inline";

    const input =
        document.createElement("input");

    input.className =
        "tr-input-field";

    input.value =
        String(
            initialValue ?? ""
        );

    input.disabled =
        disabled;

    input.oninput = () => {
        if (input.disabled) {
            return;
        }

        onChange(
            input.value
        );

        persistWorkout(
            trainingStore.workout
        );
    };

    const arrows =
        document.createElement("div");

    arrows.className =
        "tr-input-arrows";

    const up =
        document.createElement("div");

    up.className =
        "tr-arrow tr-arrow-up";

    up.onclick = () => {
        if (input.disabled) {
            return;
        }

        const value =
            String(
                input.value
            );

        if (isRange) {
            const parts =
                value
                    .split("-")
                    .map(Number);

            const first =
                Number.isFinite(
                    parts[0]
                )
                    ? parts[0]
                    : 0;

            const second =
                Number.isFinite(
                    parts[1]
                )
                    ? parts[1]
                    : first;

            const next =
                `${first + 1}-${second + 1}`;

            input.value =
                next;

            onChange(
                next
            );

            persistWorkout(
                trainingStore.workout
            );

            return;
        }

        const next =
            (Number(
                input.value
            ) || 0) + 1;

        input.value =
            String(next);

        onChange(
            next
        );

        persistWorkout(
            trainingStore.workout
        );
    };

    const down =
        document.createElement("div");

    down.className =
        "tr-arrow tr-arrow-down";

    down.onclick = () => {
        if (input.disabled) {
            return;
        }

        const value =
            String(
                input.value
            );

        if (isRange) {
            const parts =
                value
                    .split("-")
                    .map(Number);

            const first =
                Math.max(
                    1,
                    Number(
                        parts[0]
                    ) || 1
                );

            const second =
                Math.max(
                    first,
                    Number(
                        parts[1]
                    ) || first
                );

            const nextFirst =
                Math.max(
                    1,
                    first - 1
                );

            const nextSecond =
                Math.max(
                    nextFirst,
                    second - 1
                );

            const next =
                `${nextFirst}-${nextSecond}`;

            input.value =
                next;

            onChange(
                next
            );

            persistWorkout(
                trainingStore.workout
            );

            return;
        }

        const next =
            Math.max(
                0,
                (
                    Number(
                        input.value
                    ) || 0
                ) - 1
            );

        input.value =
            String(next);

        onChange(
            next
        );

        persistWorkout(
            trainingStore.workout
        );
    };

    const label =
        document.createElement("span");

    label.className =
        "tr-input-inline-label";

    label.textContent =
        labelText;

    arrows.appendChild(
        up
    );

    arrows.appendChild(
        down
    );

    wrap.appendChild(
        input
    );

    wrap.appendChild(
        arrows
    );

    wrap.appendChild(
        label
    );

    if (disabled) {
        wrap.classList.add(
            "tr-input-inline-disabled"
        );
    }

    return wrap;
}

export function renderWorkoutList(): void {
    const box =
        document.getElementById(
            "tr-workout-exercise-list"
        );

    if (!box) {
        return;
    }

    box.innerHTML = "";

    const sorted: WorkoutExercise[] =
        [
            ...trainingStore.workout
        ].sort(
            (a, b) => {
                if (
                    a.done &&
                    !b.done
                ) {
                    return 1;
                }

                if (
                    !a.done &&
                    b.done
                ) {
                    return -1;
                }

                return 0;
            }
        );

    if (!sorted.length) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "tr-session-empty";

        empty.textContent =
            t("workout.add");

        empty.onclick = () => {
            const button =
                document.getElementById(
                    "tr-add-exercise"
                );

            button?.click();
        };

        box.appendChild(
            empty
        );

        return;
    }

    sorted.forEach(
        item => {
            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "tr-session-ex-row";

            if (item.done) {
                row.classList.add(
                    "tr-ex-done"
                );
            }

            const nameWrap =
                document.createElement(
                    "div"
                );

            nameWrap.className =
                "tr-session-ex-name-wrap";

            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "tr-session-ex-name";

            name.textContent =
                item.exercise?.name ||
                t("exercise.fallback");

            nameWrap.appendChild(
                name
            );

            if (item.fromPlan) {
                const planIcon =
                    document.createElement(
                        "span"
                    );

                planIcon.className =
                    "tr-session-ex-plan-icon";

                planIcon.innerHTML =
                    ICONS.plan || "";

                nameWrap.appendChild(
                    planIcon
                );
            }

            const disabled =
                Boolean(
                    item.done
                );

            const setsBlock =
                makeInlineBlock(
                    t("exercise.sets"),
                    item.sets,
                    value => {
                        item.sets =
                            parseInt(
                                String(
                                    value
                                ),
                                10
                            ) || 0;
                    },
                    false,
                    disabled
                );

            const repsBlock =
                makeInlineBlock(
                    t("exercise.reps"),
                    item.reps,
                    value => {
                        item.reps =
                            String(
                                value
                            );
                    },
                    true,
                    disabled
                );

            const loadBlock =
                makeInlineBlock(
                    t("exercise.weight"),
                    item.load,
                    value => {
                        item.load =
                            parseFloat(
                                String(
                                    value
                                )
                            ) || 0;
                    },
                    false,
                    disabled
                );

            const check =
                document.createElement(
                    "div"
                );

            check.className =
                "tr-ex-check";

            if (item.done) {
                check.classList.add(
                    "checked"
                );
            }

            check.onclick = () => {
                item.done =
                    !item.done;

                persistWorkout(
                    trainingStore.workout
                );

                renderWorkoutList();

                window.dispatchEvent(
                    new CustomEvent(
                        "training:workout-updated"
                    )
                );
            };

            row.appendChild(
                nameWrap
            );

            row.appendChild(
                repsBlock
            );

            row.appendChild(
                setsBlock
            );

            row.appendChild(
                loadBlock
            );

            row.appendChild(
                check
            );

            box.appendChild(
                row
            );
        }
    );
}