import { TrainingAPI } from "./api.js";

export async function loadExercisesList(
    containerId: string
): Promise<void> {
    const container =
        document.getElementById(
            containerId
        );

    if (!container) {
        return;
    }

    try {
        const data =
            await TrainingAPI.getExercises();

        const items =
            Array.isArray(data)
                ? data
                : data.items || [];

        container.innerHTML = "";

        items.forEach(exercise => {
            const row =
                document.createElement("div");

            row.className =
                "tr-exercise-row";

            const name =
                document.createElement("div");

            name.className =
                "tr-exercise-name";

            name.textContent =
                exercise.name;

            const meta =
                document.createElement("div");

            meta.className =
                "tr-exercise-meta";

            meta.textContent =
                (
                    exercise.muscles_primary ||
                    []
                ).join(", ");

            row.appendChild(name);
            row.appendChild(meta);

            container.appendChild(row);
        });
    } catch {
        return;
    }
}