import { ICONS } from "../../../../icons/index.js";
import { enableDragAndDrop } from "../interactions/dragdrop.js";
import {
    createNumberField,
    createRepsField
} from "./counters.js";
import { PlanExercise } from "../state.js";

interface ExerciseCardActions {
    replace: (
        index: number
    ) => void;
    remove: (
        index: number
    ) => void;
    move: (
        fromIndex: number,
        toIndex: number
    ) => void;
}

function getExerciseName(
    exercise: any
): string {
    return (
        exercise?.name ??
        exercise?.exercise_name ??
        "Без назви"
    );
}

function createButton(
    className: string,
    content: string,
    label: string,
    onClick?: () => void
): HTMLButtonElement {
    const button =
        document.createElement(
            "button"
        );

    button.type = "button";
    button.className =
        className;

    button.setAttribute(
        "aria-label",
        label
    );

    button.innerHTML =
        content;

    if (onClick) {
        button.addEventListener(
            "click",
            onClick
        );
    }

    return button;
}

export function createExerciseCard(
    item: PlanExercise,
    index: number,
    actions: ExerciseCardActions
): HTMLDivElement {
    const card =
        document.createElement("div");

    card.className =
        "db-plan-card";

    const header =
        document.createElement("div");

    header.className =
        "db-plan-card-header";

    const left =
        document.createElement("div");

    left.className =
        "db-plan-card-header-left";

    const strip =
        document.createElement("div");

    strip.className =
        "db-plan-card-strip";

    const name =
        createButton(
            "db-plan-ex-name",
            "",
            getExerciseName(
                item.exercise
            ),
            () =>
                actions.replace(
                    index
                )
        );

    name.textContent =
        getExerciseName(
            item.exercise
        );

    left.append(
        strip,
        name
    );

    const controls =
        document.createElement("div");

    controls.className =
        "db-plan-card-header-right";

    controls.append(
        createButton(
            "db-plan-card-drag",
            ICONS.grip,
            "Змінити порядок"
        ),
        createButton(
            "db-plan-card-delete",
            ICONS.delete,
            "Видалити вправу",
            () =>
                actions.remove(
                    index
                )
        )
    );

    header.append(
        left,
        controls
    );

    const body =
        document.createElement("div");

    body.className =
        "db-plan-card-body";

    body.append(
        createRepsField(
            item.reps,
            value => {
                item.reps =
                    value;
            }
        ),
        createNumberField(
            "Підходи",
            ICONS.exercise,
            item.sets,
            value => {
                item.sets =
                    value;
            }
        ),
        createNumberField(
            "Вага (кг)",
            ICONS.exercise,
            item.load,
            value => {
                item.load =
                    value;
            }
        )
    );

    card.append(
        header,
        body
    );

    enableDragAndDrop(
        card,
        index,
        actions.move
    );

    return card;
}