import { TrainingAPI } from "./api.js";

export async function loadExercisesList(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    try {
        const data = await TrainingAPI.getExercises();
        const items = data.items || data || [];
        container.innerHTML = "";
        items.forEach(ex => {
            const row = document.createElement("div");
            row.className = "tr-exercise-row";
            const name = document.createElement("div");
            name.className = "tr-exercise-name";
            name.textContent = ex.name;
            const meta = document.createElement("div");
            meta.className = "tr-exercise-meta";
            meta.textContent = (ex.muscles_primary || []).join(", ");
            row.appendChild(name);
            row.appendChild(meta);
            container.appendChild(row);
        });
    } catch (_) {}
}
