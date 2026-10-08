import { trainingStore } from "./store.js";
import { persistWorkout } from "./state.js";
import { ICONS } from "../icons/index.js";
import { isDurationExercise, isPerSide } from "./measurement.js";
import { acceptsLoad, entriesOf, syncTotals } from "./sets.js";
function measurementLabel(item, key) {
    return isPerSide(item.exercise)
        ? `${t(key)} ${t("exercise.perSide")}`
        : t(key);
}
import { exercise_t, t } from "../i18n/index.js";
function getExerciseName(item) {
    const slug = item.exercise?.slug;
    if (typeof slug === "string" &&
        slug.trim()) {
        const translated = exercise_t(slug);
        if (translated !==
            `${slug}.name`) {
            return translated;
        }
    }
    return (item.exercise?.name ||
        t("exercise.fallback"));
}
function makeNumberInput(value, disabled, onChange, step = "1") {
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = step;
    input.inputMode = step === "1" ? "numeric" : "decimal";
    input.className = "tr-input-field tr-set-input";
    input.value = value != null && value !== 0 ? String(value) : "";
    input.disabled = disabled;
    input.oninput = () => {
        onChange(Number(input.value.replace(",", ".")) || 0);
    };
    return input;
}
// One row per set: "1  [12] повт.  [60] кг  ✕", then "+ Підхід" that
// copies the last set. Each set keeps its own reps and kg.
function makeSetsEditor(item, disabled) {
    const box = document.createElement("div");
    box.className =
        "tr-sets-editor";
    const duration = isDurationExercise(item.exercise);
    const withLoad = acceptsLoad(item.exercise);
    const entries = entriesOf(item);
    const changed = () => {
        syncTotals(item);
        persistWorkout(trainingStore.workout);
    };
    entries.forEach((entry, index) => {
        const row = document.createElement("div");
        row.className =
            "tr-set-row";
        const number = document.createElement("span");
        number.className =
            "tr-set-num";
        number.textContent =
            String(index + 1);
        row.appendChild(number);
        row.appendChild(makeNumberInput(duration ? entry.duration_sec : entry.reps, disabled, value => {
            if (duration) {
                entry.duration_sec = Math.round(value);
            }
            else {
                entry.reps = Math.round(value);
            }
            changed();
        }));
        const unit = document.createElement("span");
        unit.className =
            "tr-set-unit";
        unit.textContent =
            duration
                ? measurementLabel(item, "exercise.seconds")
                : measurementLabel(item, "exercise.reps");
        row.appendChild(unit);
        if (withLoad) {
            row.appendChild(makeNumberInput(entry.load, disabled, value => {
                entry.load = value;
                changed();
            }, "0.5"));
            const kg = document.createElement("span");
            kg.className =
                "tr-set-unit";
            kg.textContent =
                t("exercise.weight");
            row.appendChild(kg);
        }
        if (!disabled && entries.length > 1) {
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "tr-set-remove";
            remove.textContent = "✕";
            remove.title = t("exercise.removeSet");
            remove.onclick = () => {
                entries.splice(index, 1);
                changed();
                renderWorkoutList();
            };
            row.appendChild(remove);
        }
        box.appendChild(row);
    });
    if (!disabled) {
        const add = document.createElement("button");
        add.type = "button";
        add.className = "tr-set-add";
        add.textContent = t("exercise.addSet");
        add.onclick = () => {
            const last = entries[entries.length - 1];
            entries.push(last
                ? { ...last }
                : duration
                    ? { duration_sec: 30, load: 0 }
                    : { reps: 10, load: 0 });
            changed();
            renderWorkoutList();
        };
        box.appendChild(add);
    }
    return box;
}
export function renderWorkoutList() {
    const box = document.getElementById("tr-workout-exercise-list");
    if (!box) {
        return;
    }
    box.innerHTML = "";
    const sorted = [
        ...trainingStore.workout
    ].sort((a, b) => {
        if (a.done &&
            !b.done) {
            return 1;
        }
        if (!a.done &&
            b.done) {
            return -1;
        }
        return 0;
    });
    if (!sorted.length) {
        const empty = document.createElement("div");
        empty.className =
            "tr-session-empty";
        empty.textContent =
            t("workout.add");
        empty.onclick = () => {
            const button = document.getElementById("tr-add-exercise");
            button?.click();
        };
        box.appendChild(empty);
        return;
    }
    sorted.forEach(item => {
        const row = document.createElement("div");
        row.className =
            "tr-session-ex-row";
        if (item.done) {
            row.classList.add("tr-ex-done");
        }
        const nameWrap = document.createElement("div");
        nameWrap.className =
            "tr-session-ex-name-wrap";
        const name = document.createElement("div");
        name.className =
            "tr-session-ex-name";
        name.textContent =
            getExerciseName(item);
        nameWrap.appendChild(name);
        if (item.fromPlan) {
            const planIcon = document.createElement("span");
            planIcon.className =
                "tr-session-ex-plan-icon";
            planIcon.innerHTML =
                ICONS.plan || "";
            nameWrap.appendChild(planIcon);
        }
        const disabled = Boolean(item.done);
        const setsEditor = makeSetsEditor(item, disabled);
        const check = document.createElement("div");
        check.className =
            "tr-ex-check";
        if (item.done) {
            check.classList.add("checked");
        }
        check.onclick = () => {
            item.done =
                !item.done;
            persistWorkout(trainingStore.workout);
            renderWorkoutList();
            window.dispatchEvent(new CustomEvent("training:workout-updated"));
        };
        row.appendChild(nameWrap);
        row.appendChild(setsEditor);
        row.appendChild(check);
        box.appendChild(row);
    });
}
