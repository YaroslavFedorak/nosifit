import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { renderWorkoutList } from "./workout.js";
import { t } from "../i18n/index.js";
import { isDurationExercise } from "./measurement.js";
import { persistSessionId } from "./state.js";
import { entriesOf } from "./sets.js";
export function initSession() {
    const saveButton = document.getElementById("tr-save-workout");
    const titleInput = document.getElementById("tr-workout-title");
    if (!saveButton) {
        return;
    }
    saveButton.onclick =
        async () => {
            const selected = trainingStore.workout.filter(item => item.done);
            const payload = {
                // Re-saving today's workout updates the same session.
                session_id: trainingStore.sessionId,
                title: titleInput?.value ||
                    null,
                exercises: selected.map(item => ({
                    exercise: {
                        id: item.exercise.id
                    },
                    sets: item.sets,
                    ...(isDurationExercise(item.exercise)
                        ? { duration_sec: item.duration_sec }
                        : { reps: item.reps }),
                    load: item.load,
                    set_entries: entriesOf(item),
                    ...(item.rpe != null
                        ? { rpe: item.rpe }
                        : {})
                }))
            };
            try {
                const response = await TrainingAPI.completeSession(payload);
                trainingStore.sessionId =
                    response.id;
                persistSessionId(response.id);
                showSavedToast();
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
            catch {
                return;
            }
        };
}
function showSavedToast() {
    const toast = document.createElement("div");
    toast.className =
        "tr-toast-saved";
    toast.textContent =
        t("session.saved");
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("show");
    }, 10);
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 2500);
}
