import { defaultPrescription } from "../measurement.js";
import { initState, loadStateFromPlan, state } from "./state.js";
import { allowedEquipment } from "./availability.js";
import { renderDayPanel } from "./ui/dayPanel.js";
import { initGenerate } from "./ui/generate.js";
import { loadWeek } from "./services/week.js";
import { dom } from "./dom.js";
import { t } from "../../i18n/index.js";
import { DAYS, isPlanDayKey } from "./constants.js";
import { renderExercises } from "./ui/render.js";
import { savePlan } from "./services/save.js";
import { openExercisePicker } from "../exercise_picker.js";
import { trainingStore } from "../store.js";
import { renderWorkoutList } from "../workout.js";
// The picker for the day being edited: exercises that need equipment the day
// does not have are shown but cannot be chosen.
const pickForDay = callback => {
    openExercisePicker(callback, {
        allowed: allowedEquipment(state.meta[state.currentDay])
    });
};
function refreshDay() {
    dom.dayButtons?.forEach(item => {
        const current = item.dataset.day ===
            state.currentDay;
        item.classList.toggle("active", current);
        item.setAttribute("aria-pressed", String(current));
    });
    renderExercises(pickForDay);
    renderDayPanel(refreshDay);
}
function renderDays() {
    const container = document.getElementById("tr-plan-days");
    if (!container) {
        return;
    }
    container.innerHTML = "";
    DAYS.forEach(day => {
        const button = document.createElement("button");
        button.type =
            "button";
        button.className =
            "tr-plan-day";
        button.dataset.day =
            day.key;
        button.innerHTML = `
                <span>${t(`weekdays.${day.key}`)}</span>
                <span
                    class="tr-plan-day-badge"
                    data-day-badge="${day.key}"
                ></span>
            `;
        container.appendChild(button);
    });
    dom.dayButtons =
        Array.from(container.querySelectorAll(".tr-plan-day"));
}
function syncPlanToSession() {
    const allExercises = Object.values(state.days).flat();
    trainingStore.workout =
        trainingStore.workout.filter(item => !item.fromPlan);
    allExercises.forEach(item => {
        trainingStore.workout.push({
            exercise: item.exercise,
            sets: item.sets,
            reps: item.reps,
            duration_sec: item.duration_sec,
            load: item.load,
            done: true,
            fromPlan: true
        });
    });
    trainingStore.workout.sort((a, b) => {
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
    renderWorkoutList();
}
export function initPlanModal() {
    if (!dom.modal) {
        return;
    }
    renderDays();
    initState();
    initGenerate(refreshDay);
    dom.dayButtons?.forEach(button => {
        button.onclick = () => {
            const day = button.dataset.day;
            if (!day ||
                !isPlanDayKey(day)) {
                return;
            }
            state.currentDay =
                day;
            dom.dayButtons.forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            refreshDay();
        };
    });
    if (dom.addBtn) {
        dom.addBtn.onclick = () => {
            pickForDay(exercise => {
                const prescription = defaultPrescription(exercise);
                state.days[state.currentDay].push({
                    exercise,
                    sets: prescription.sets,
                    reps: prescription.reps,
                    duration_sec: prescription.duration_sec,
                    load: 0
                });
                refreshDay();
            });
        };
    }
    if (dom.emptyAddBtn) {
        dom.emptyAddBtn.onclick =
            () => {
                dom.addBtn?.click();
            };
    }
    if (dom.helpToggle &&
        dom.helpPopover) {
        dom.helpToggle.onclick =
            () => {
                dom.helpPopover?.classList.toggle("open");
            };
    }
    if (dom.saveBtn) {
        dom.saveBtn.onclick =
            async () => {
                if (await savePlan()) {
                    syncPlanToSession();
                    await loadWeek();
                    refreshDay();
                }
            };
    }
    if (dom.openBtn) {
        dom.openBtn.onclick =
            async () => {
                loadStateFromPlan();
                if (dom.titleInput) {
                    dom.titleInput.value =
                        trainingStore.plan?.name ||
                            t("plan.defaultName");
                }
                document
                    .getElementById("tr-plan-explain")
                    ?.classList.add("hidden");
                refreshDay();
                dom.modal?.classList.add("open");
                await loadWeek();
                refreshDay();
            };
    }
    dom.closeBtns?.forEach(button => {
        button.onclick =
            () => {
                dom.modal?.classList.remove("open");
            };
    });
}
