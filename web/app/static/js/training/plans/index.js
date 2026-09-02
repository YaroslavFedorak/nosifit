import { initState, state } from "./state.js";
import { dom } from "./dom.js";
import { DAYS } from "./constants.js";
import { renderExercises } from "./ui/render.js";
import { savePlan } from "./services/save.js";
import { openExercisePicker } from "../exercise_picker.js";
import { trainingStore } from "../store.js";
import { renderWorkoutList } from "../workout.js";

function renderDays() {
    const container = document.getElementById("tr-plan-days");
    if (!container) return;

    container.innerHTML = "";

    DAYS.forEach(day => {
        const btn = document.createElement("button");
        btn.className = "tr-plan-day";
        btn.dataset.day = day.key;
        btn.innerHTML = `
            <span>${day.short}</span>
            <span class="tr-plan-day-badge" data-day-badge="${day.key}"></span>
        `;
        container.appendChild(btn);
    });

    dom.dayButtons = container.querySelectorAll(".tr-plan-day");
}

function syncPlanToSession() {
    const allExercises = [];
    Object.keys(state.days).forEach(dayKey => {
        const list = state.days[dayKey] || [];
        list.forEach(item => {
            allExercises.push(item);
        });
    });

    trainingStore.workout = trainingStore.workout.filter(item => !item.fromPlan);

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
        if (a.done && !b.done) return 1;
        if (!a.done && b.done) return -1;
        return 0;
    });

    renderWorkoutList();
}

export function initPlanModal() {
    if (!dom.modal) return;

    renderDays();
    initState();

    if (dom.dayButtons) {
        dom.dayButtons.forEach(btn => {
            btn.onclick = () => {
                state.currentDay = btn.dataset.day;
                dom.dayButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                renderExercises(openExercisePicker);
            };
        });
    }

    if (dom.addBtn) {
        dom.addBtn.onclick = () => {
            openExercisePicker(ex => {
                state.days[state.currentDay].push({
                    exercise: ex,
                    sets: 3,
                    reps: "8–12",
                    load: 0
                });
                renderExercises(openExercisePicker);
            });
        };
    }

    if (dom.emptyAddBtn) {
        dom.emptyAddBtn.onclick = () => dom.addBtn?.click();
    }

    if (dom.helpToggle) {
        dom.helpToggle.onclick = () => {
            dom.helpPopover.classList.toggle("open");
        };
    }

    if (dom.saveBtn) {
        dom.saveBtn.onclick = async () => {
            try {
                await savePlan();
                syncPlanToSession();
            } catch (_) {}
        };
    }

    if (dom.openBtn) {
        dom.openBtn.onclick = () => {
            initState(true);
            dom.titleInput.value = window.trainingStore.plan?.name || "Мій план";
            renderExercises(openExercisePicker);
            dom.modal.classList.add("open");
        };
    }

    if (dom.closeBtns) {
        dom.closeBtns.forEach(btn => {
            btn.onclick = () => dom.modal.classList.remove("open");
        });
    }
}
