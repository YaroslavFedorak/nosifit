import * as state from "./state.js";
import { render } from "./renderer.js";
import { bind } from "./events.js";

let container = null;
let initialized = false;

function getContainer() {
    if (container) return container;
    container = document.getElementById("dashboard-workout-exercise-list");
    return container;
}

function rerender() {
    const target = getContainer();
    if (!target) return;
    render(target);
}

export function init() {
    const target = getContainer();
    if (!target) {
        console.warn("Training container was not found");
        return;
    }
    if (!initialized) {
        bind(target, {
            onChange() {
                rerender();
            }
        });
        initialized = true;
    }
    rerender();
}

export function addExercise(exercise) {
    const added = state.addExercise(exercise);
    rerender();
    return added;
}

export function removeExercise(id) {
    const removed = state.removeExercise(id);
    rerender();
    return removed;
}

export function updateExercise(id, field, value) {
    const updated = state.updateExercise(id, field, value);
    rerender();
    return updated;
}

export function getExercises() {
    return state.getExercises();
}

export function getCompletedExercises() {
    return state.getCompletedExercises();
}

export function replaceExercises(exercises) {
    state.replaceExercises(exercises);
    rerender();
}

export function clear() {
    state.clear();
    rerender();
}

export function hasExercises() {
    return state.hasExercises();
}

export function hasCompletedExercises() {
    return state.hasCompletedExercises();
}

const trainingEditor = {
    init,
    addExercise,
    removeExercise,
    updateExercise,
    getExercises,
    getCompletedExercises,
    replaceExercises,
    clear,
    hasExercises,
    hasCompletedExercises
};

export default trainingEditor;
