import { createCounterField, createRepsField } from "./counters.js";
import { enableDrag } from "../interactions/dragdrop.js";
import { defaultPrescription, isDurationExercise, isPerSide } from "../../measurement.js";
import { ICONS } from "../../../icons/index.js";
import { exercise_t, t } from "../../../i18n/index.js";
import { escapeHtml } from "../../../utils/html.js";
function getExerciseName(exercise) {
    if (!exercise.slug) {
        return exercise.name;
    }
    const translated = exercise_t(exercise.slug);
    return translated ===
        `${exercise.slug}.name`
        ? exercise.name
        : translated;
}
export function createExerciseCard(exercise, index, list, rerender, openPicker) {
    const card = document.createElement("div");
    card.className =
        "tr-plan-card";
    const name = getExerciseName(exercise.exercise);
    card.innerHTML = `
    <div class="tr-plan-card-header">
        <div class="tr-plan-card-header-left">
            <div class="tr-plan-card-strip"></div>
            <button class="tr-plan-ex-name">
                ${escapeHtml(name)}
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
    const reps = isDurationExercise(exercise.exercise)
        ? createCounterField(isPerSide(exercise.exercise)
            ? `${t("exercise.seconds")} ${t("exercise.perSide")}`
            : t("exercise.seconds"), ICONS.exercise, exercise.duration_sec ?? 0, value => {
            exercise.duration_sec =
                value;
        })
        : createRepsField(exercise.reps ?? "", value => {
            exercise.reps =
                value;
        }, isPerSide(exercise.exercise)
            ? `${t("exercise.reps")} ${t("exercise.perSide")}`
            : t("exercise.reps"));
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
            const prescription = defaultPrescription(selectedExercise);
            exercise.exercise =
                selectedExercise;
            exercise.reps =
                prescription.reps;
            exercise.duration_sec =
                prescription.duration_sec;
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
