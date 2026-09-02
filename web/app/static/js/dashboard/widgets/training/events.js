import * as state from "./state.js";

function getExerciseId(target) {
    return target.dataset.exerciseId || null;
}

export function bind(container, options = {}) {
    if (!container) return;

    container.addEventListener("click", event => {
        const target = event.target.closest("[data-action]");
        if (!target) return;

        const id = target.dataset.exerciseId;
        const action = target.dataset.action;
        const field = target.dataset.field;

        if (!id || !action) return;

        const exercise = state.getExerciseById(id);
        if (!exercise) return;

        if (action === "toggle") {
            state.toggleExercise(id);
            options.onChange?.();
            return;
        }

        if (exercise.completed) return;

        if (action === "arrow-up") {
            let value = Number(exercise[field]) || 0;
            value++;
            state.updateExercise(id, field, value);
            options.onChange?.();
            return;
        }

        if (action === "arrow-down") {
            let value = Number(exercise[field]) || 0;
            value = Math.max(0, value - 1);
            state.updateExercise(id, field, value);
            options.onChange?.();
            return;
        }
    });

    container.addEventListener("change", event => {
        const input = event.target;
        const id = input.dataset.exerciseId;
        const field = input.dataset.field;

        if (!id || !field) return;

        const exercise = state.getExerciseById(id);
        if (!exercise || exercise.completed) return;

        let value = input.value.trim();

        if (field === "sets" || field === "weight") {
            value = Number(value) || 0;
        }

        state.updateExercise(id, field, value);
        options.onFieldChange?.({ id, field, value });
    });
}
