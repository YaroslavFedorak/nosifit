import { trainingStore } from "../../store.js";
import { t } from "../../../i18n/index.js";
import { EQUIPMENT, LOCATIONS, OUTDOOR_EQUIPMENT } from "../constants.js";
import { state } from "../state.js";
import { completeCurrentDay } from "../services/week.js";
// The equipment list is long; it stays folded until asked for, and stays as
// the user left it while the panel is redrawn.
let equipmentOpen = false;
function button(label, pressed, onClick, className) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = className;
    element.textContent = label;
    element.setAttribute("aria-pressed", String(pressed));
    if (pressed) {
        element.classList.add("active");
    }
    element.onclick = onClick;
    return element;
}
function field(label, content) {
    const wrapper = document.createElement("div");
    wrapper.className = "tr-plan-field";
    const title = document.createElement("span");
    title.className = "tr-plan-field-label";
    title.textContent = label;
    wrapper.append(title, content);
    return wrapper;
}
function locationControl(redraw) {
    const meta = state.meta[state.currentDay];
    const group = document.createElement("div");
    group.className = "tr-plan-segmented";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", t("plan.location.label"));
    LOCATIONS.forEach((location) => {
        group.appendChild(button(t(`plan.location.${location}`), meta.location === location, () => {
            // Choosing the place again clears it.
            meta.location =
                meta.location === location
                    ? null
                    : location;
            // A gym is not limited to a list of equipment.
            if (meta.location === "gym") {
                meta.equipment = null;
            }
            redraw();
        }, "tr-plan-seg-btn"));
    });
    return field(t("plan.location.label"), group);
}
function equipmentControl(redraw) {
    const meta = state.meta[state.currentDay];
    // Only a home or an outdoor session needs a list of what is at hand.
    if (meta.location !== "home" &&
        meta.location !== "outdoors") {
        return null;
    }
    const options = meta.location === "outdoors"
        ? EQUIPMENT.filter(slug => OUTDOOR_EQUIPMENT.includes(slug))
        : EQUIPMENT;
    const group = document.createElement("div");
    group.className = "tr-plan-chips";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", t("plan.equipmentLabel"));
    group.appendChild(button(t("plan.equipmentAny"), meta.equipment === null, () => {
        meta.equipment = null;
        redraw();
    }, "tr-plan-chip"));
    options.forEach(slug => {
        group.appendChild(button(t(`plan.equipmentNames.${slug}`), meta.equipment?.includes(slug) ?? false, () => {
            const current = meta.equipment ?? [];
            meta.equipment =
                current.includes(slug)
                    ? current.filter(item => item !== slug)
                    : [...current, slug];
            redraw();
        }, "tr-plan-chip"));
    });
    const names = meta.equipment === null
        ? t("plan.equipmentAny")
        : meta.equipment.length
            ? meta.equipment
                .map(slug => t(`plan.equipmentNames.${slug}`))
                .join(", ")
            : t("plan.equipmentNone");
    const wrapper = document.createElement("details");
    wrapper.className = "tr-plan-field tr-plan-equipment";
    wrapper.open = equipmentOpen;
    wrapper.ontoggle = () => {
        equipmentOpen = wrapper.open;
    };
    const summary = document.createElement("summary");
    summary.className = "tr-plan-field-label";
    summary.textContent =
        `${t("plan.equipmentLabel")}: ${names}`;
    wrapper.append(summary, group);
    return wrapper;
}
function completionControl(redraw) {
    const exercises = state.days[state.currentDay].length;
    if (!exercises) {
        return null;
    }
    const row = document.createElement("div");
    row.className = "tr-plan-complete";
    const planId = trainingStore.plan?.id;
    const day = state.week?.days.find(item => item.key === state.currentDay);
    const done = day?.completed === true;
    const future = day !== undefined &&
        day.date > (state.week?.today ?? "");
    const action = document.createElement("button");
    action.type = "button";
    action.className =
        "tr-btn tr-btn-ghost tr-plan-complete-btn";
    action.textContent =
        done
            ? `✓ ${t("plan.completed")}`
            : t("plan.complete");
    action.disabled =
        done || future || !planId;
    if (done) {
        action.classList.add("done");
    }
    action.onclick = async () => {
        action.disabled = true;
        await completeCurrentDay();
        redraw();
    };
    const note = document.createElement("small");
    note.className = "tr-plan-hint";
    if (done) {
        note.textContent =
            t("plan.completedNote");
    }
    else if (!planId) {
        note.textContent =
            t("plan.saveFirst");
    }
    else if (future) {
        note.textContent =
            t("plan.futureDay");
    }
    row.append(action, note);
    return row;
}
export function renderDayPanel(onChange) {
    const panel = document.getElementById("tr-plan-day-panel");
    if (!panel) {
        return;
    }
    const redraw = () => {
        onChange();
        renderDayPanel(onChange);
    };
    panel.replaceChildren();
    panel.appendChild(locationControl(redraw));
    const equipment = equipmentControl(redraw);
    if (equipment) {
        panel.appendChild(equipment);
    }
    const completion = completionControl(redraw);
    if (completion) {
        panel.appendChild(completion);
    }
}
