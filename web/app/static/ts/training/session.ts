import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
import { renderWorkoutList } from "./workout.js";

export function initSession(): void {
    const saveButton =
        document.getElementById(
            "tr-save-workout"
        );

    const titleInput =
        document.getElementById(
            "tr-workout-title"
        ) as HTMLInputElement | null;

    if (!saveButton) {
        return;
    }

    saveButton.onclick =
        async () => {
            const selected =
                trainingStore.workout.filter(
                    item => item.done
                );

            const payload = {
                title:
                    titleInput?.value ||
                    null,
                exercises:
                    selected.map(item => ({
                        exercise: {
                            id: item.exercise.id
                        },
                        sets: item.sets,
                        reps: item.reps,
                        load: item.load
                    }))
            };

            try {
                const response =
                    await TrainingAPI.completeSession(
                        payload
                    );

                trainingStore.sessionId =
                    response.id;

                showSavedToast();

                trainingStore.workout.sort(
                    (a, b) => {
                        if (
                            a.done &&
                            !b.done
                        ) {
                            return 1;
                        }

                        if (
                            !a.done &&
                            b.done
                        ) {
                            return -1;
                        }

                        return 0;
                    }
                );

                renderWorkoutList();
            } catch {
                return;
            }
        };
}

function showSavedToast(): void {
    const toast =
        document.createElement("div");

    toast.className =
        "tr-toast-saved";

    toast.textContent =
        "Тренування збережене";

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