import { initState, state } from "./state.js";
import { dom } from "./dom.js";
import { DAYS, isPlanDayKey } from "./constants.js";
import { renderExercises } from "./ui/render.js";
import { savePlan } from "./services/save.js";
import { openExercisePicker } from "../exercise_picker.js";
import { trainingStore } from "../store.js";
import { renderWorkoutList } from "../workout.js";
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
                <span>${day.short}</span>
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
            renderExercises(openExercisePicker);
        };
    });
    if (dom.addBtn) {
        dom.addBtn.onclick = () => {
            openExercisePicker(exercise => {
                state.days[state.currentDay].push({
                    exercise,
                    sets: 3,
                    reps: "8–12",
                    load: 0
                });
                renderExercises(openExercisePicker);
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
                try {
                    await savePlan();
                    syncPlanToSession();
                }
                catch {
                    return;
                }
            };
    }
    if (dom.openBtn) {
        dom.openBtn.onclick =
            () => {
                initState(true);
                if (dom.titleInput) {
                    dom.titleInput.value =
                        trainingStore.plan?.name ||
                            "Мій план";
                }
                renderExercises(openExercisePicker);
                dom.modal?.classList.add("open");
            };
    }
    dom.closeBtns?.forEach(button => {
        button.onclick =
            () => {
                dom.modal?.classList.remove("open");
            };
    });
}
