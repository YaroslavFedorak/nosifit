import { ApiError, TrainingAPI } from "../../api.js";
import { t } from "../../../i18n/index.js";
import { DAYS } from "../constants.js";
import { dom } from "../dom.js";
import { normalize, normalizeMeta, state } from "../state.js";
import { showToast } from "./toast.js";
// Muscle slugs from the server are kebab-case; the translations are camelCase.
function muscleName(slug) {
    const key = slug.replace(/-(\w)/g, (_, letter) => letter.toUpperCase());
    const translated = t(`muscles.${key}`);
    return translated === `muscles.${key}`
        ? slug
        : translated;
}
function dayName(key) {
    return t(`weekdays.${key}`);
}
function noteText(note) {
    const text = (key, params = {}) => t(`plan.explain.notes.${key}`, params);
    const muscles = (note.muscles ?? [])
        .map(muscleName)
        .join(", ");
    switch (note.code) {
        case "volume_short":
        case "volume_high":
        case "split_skips":
            return text(note.code, { muscles });
        case "no_exercises":
            return note.day
                ? text(note.code, { day: dayName(note.day) })
                : null;
        case "back_to_back":
            return text(note.code, {
                days: (note.days ?? [])
                    .map(dayName)
                    .join(", "),
                muscles
            });
        case "injuries_not_considered":
            return text(note.code);
        default:
            return null;
    }
}
// A short, plain explanation of the generated week.
function renderExplanation(plan) {
    const box = document.getElementById("tr-plan-explain");
    if (!box) {
        return;
    }
    box.replaceChildren();
    const title = document.createElement("strong");
    title.textContent =
        t("plan.explain.title");
    const list = document.createElement("ul");
    DAYS.forEach(day => {
        const info = plan.explanation[day.key];
        if (!info) {
            return;
        }
        const item = document.createElement("li");
        item.textContent =
            `${dayName(day.key)}: ${t(`plan.explain.labels.${info.label}`)} — ${info.muscles
                .map(muscleName)
                .join(", ")}`;
        list.appendChild(item);
    });
    plan.notes.forEach(note => {
        const text = noteText(note);
        if (!text) {
            return;
        }
        const item = document.createElement("li");
        item.className = "note";
        item.textContent = text;
        list.appendChild(item);
    });
    box.append(title, list);
    box.classList.remove("hidden");
}
function selectedDays() {
    return Array.from(document.querySelectorAll("#tr-plan-generate-days input:checked")).map(input => input.value);
}
function applyDraft(plan) {
    state.days = normalize(plan.days);
    state.meta = normalizeMeta(plan.days);
    state.generated = plan;
    renderExplanation(plan);
}
function hasExercises() {
    return DAYS.some(day => state.days[day.key].length > 0);
}
// Premium: ask the server for a recommended week. The draft only fills the
// editor; nothing is saved until the user presses Save.
export function initGenerate(onApplied) {
    const toggle = document.getElementById("tr-plan-generate");
    const panel = document.getElementById("tr-plan-generate-panel");
    const run = document.getElementById("tr-plan-generate-run");
    const days = document.getElementById("tr-plan-generate-days");
    if (!toggle ||
        !panel ||
        !run ||
        !days) {
        return;
    }
    const premium = dom.modal?.dataset.premium === "true";
    days.replaceChildren(...DAYS.map(day => {
        const label = document.createElement("label");
        label.className = "tr-plan-chip tr-plan-chip-check";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = day.key;
        const text = document.createElement("span");
        text.textContent =
            dayName(day.key);
        label.append(input, text);
        return label;
    }));
    toggle.onclick = () => {
        if (!premium) {
            showToast(t("plan.generate.premiumRequired"));
            return;
        }
        const open = panel.classList.toggle("hidden") === false;
        toggle.setAttribute("aria-expanded", String(open));
    };
    run.onclick = async () => {
        const chosen = selectedDays();
        if (!chosen.length) {
            return;
        }
        if (hasExercises() &&
            !window.confirm(t("plan.generate.replace"))) {
            return;
        }
        run.disabled = true;
        run.textContent =
            t("plan.generate.running");
        try {
            applyDraft(await TrainingAPI.generatePlan({
                training_days: chosen,
                days: Object.fromEntries(chosen.map(key => [
                    key,
                    {
                        ...(state.meta[key].location
                            ? { location: state.meta[key].location }
                            : {}),
                        ...(state.meta[key].equipment
                            ? { equipment: state.meta[key].equipment }
                            : {})
                    }
                ]))
            }));
            panel.classList.add("hidden");
            onApplied();
            showToast(t("plan.generate.done"));
        }
        catch (error) {
            showToast(error instanceof ApiError &&
                error.code === "premium_required"
                ? t("plan.generate.premiumRequired")
                : t("plan.generate.error"));
        }
        finally {
            run.disabled = false;
            run.textContent =
                t("plan.generate.run");
        }
    };
}
