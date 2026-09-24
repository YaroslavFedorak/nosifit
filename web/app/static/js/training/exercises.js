import { trainingStore } from "./store.js";
export function loadExercisesList(containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    container.innerHTML = "";
    trainingStore.exercises.forEach(exercise => {
        const row = document.createElement("div");
        row.className =
            "tr-exercise-row";
        const name = document.createElement("div");
        name.className =
            "tr-exercise-name";
        name.textContent =
            exercise.name;
        const meta = document.createElement("div");
        meta.className =
            "tr-exercise-meta";
        meta.textContent =
            (exercise.muscles_primary ||
                []).join(", ");
        row.appendChild(name);
        row.appendChild(meta);
        container.appendChild(row);
    });
}
