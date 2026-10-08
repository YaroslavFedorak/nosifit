import { dashboard_t, exercise_t } from "../../../../i18n/index.js";
import { ICONS } from "../../../../icons/index.js";
import { enableDragAndDrop } from "../interactions/dragdrop.js";
import { createNumberField, createRepsField } from "./counters.js";
import { isDurationExercise, isPerSide } from "../../../../training/measurement.js";
function withSide(item, label) {
    const perSide = item.exercise?.per_side ??
        isPerSide(item.exercise);
    return perSide
        ? `${label} ${dashboard_t("workout.fields.perSide")}`
        : label;
}
function getExerciseName(exercise) {
    const slug = exercise?.slug ??
        exercise?.exercise_slug ??
        exercise?.original?.slug ??
        exercise?.exercise?.slug;
    if (slug) {
        const translated = exercise_t(slug);
        if (translated !==
            `${slug}.name`) {
            return translated;
        }
    }
    return (exercise?.name ??
        exercise?.exercise_name ??
        dashboard_t("workout.unnamedExercise"));
}
function createButton(className, content, label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className =
        className;
    button.setAttribute("aria-label", label);
    button.innerHTML =
        content;
    if (onClick) {
        button.addEventListener("click", onClick);
    }
    return button;
}
export function createExerciseCard(item, index, actions) {
    const card = document.createElement("div");
    card.className =
        "db-plan-card";
    const header = document.createElement("div");
    header.className =
        "db-plan-card-header";
    const left = document.createElement("div");
    left.className =
        "db-plan-card-header-left";
    const strip = document.createElement("div");
    strip.className =
        "db-plan-card-strip";
    const exerciseName = getExerciseName(item.exercise);
    const name = createButton("db-plan-ex-name", "", exerciseName, () => actions.replace(index));
    name.textContent =
        exerciseName;
    left.append(strip, name);
    const controls = document.createElement("div");
    controls.className =
        "db-plan-card-header-right";
    controls.append(createButton("db-plan-card-drag", ICONS.grip, dashboard_t("plan.actions.reorder")), createButton("db-plan-card-delete", ICONS.delete, dashboard_t("plan.actions.deleteExercise"), () => actions.remove(index)));
    header.append(left, controls);
    const body = document.createElement("div");
    body.className =
        "db-plan-card-body";
    body.append(isDurationExercise(item.exercise)
        ? createNumberField(withSide(item, dashboard_t("plan.fields.seconds")), ICONS.exercise, item.duration_sec ?? 0, value => {
            item.duration_sec =
                value;
        })
        : createRepsField(item.reps ?? "", value => {
            item.reps =
                value;
        }, withSide(item, dashboard_t("plan.fields.reps"))), createNumberField(dashboard_t("plan.fields.sets"), ICONS.exercise, item.sets, value => {
        item.sets =
            value;
    }), createNumberField(dashboard_t("plan.fields.weight"), ICONS.exercise, item.load, value => {
        item.load =
            value;
    }));
    card.append(header, body);
    enableDragAndDrop(card, index, actions.move);
    return card;
}
