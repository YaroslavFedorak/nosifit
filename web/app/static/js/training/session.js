import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { renderWorkoutList } from "./workout.js";

export function initSession() {
    const saveBtn = document.getElementById("tr-save-workout");
    const titleInput = document.getElementById("tr-workout-title");

    if (saveBtn) {
        saveBtn.onclick = async () => {
            const selected = trainingStore.workout.filter(item => item.done);

            const payload = {
                title: titleInput?.value || null,
                exercises: selected.map(item => ({
                    exercise: { id: item.exercise.id },
                    sets: item.sets,
                    reps: item.reps,
                    load: item.load
                }))
            };

            try {
                const res = await TrainingAPI.completeSession(payload);
                trainingStore.sessionId = res.id;

                showSavedToast();

                trainingStore.workout.sort((a, b) => {
                    if (a.done && !b.done) return 1;
                    if (!a.done && b.done) return -1;
                    return 0;
                });

                renderWorkoutList();
            } catch (_) {}
        };
    }
}

function showSavedToast() {
    const toast = document.createElement("div");
    toast.className = "tr-toast-saved";
    toast.textContent = "Тренування збережене";

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 10);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
