import * as state from "./state.js";
import { render } from "./renderer.js";
import { bind } from "./events.js";

let container: HTMLElement | null = null;

let initialized = false;

function getContainer(): HTMLElement | null {
    if (container) {
        return container;
    }

    container =
        document.getElementById(
            "dashboard-workout-exercise-list"
        );

    return container;
}

function rerender(): void {
    const target =
        getContainer();

    if (!target) {
        return;
    }

    render(target);
}

export function init(): void {
    const target =
        getContainer();

    if (!target) {
        console.warn(
            "Training container was not found"
        );

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

export function addExercise(
    exercise: any
): any {
    const added =
        state.addExercise(exercise);

    rerender();

    return added;
}

export function removeExercise(
    id: string
): boolean {
    const removed =
        state.removeExercise(id);

    rerender();

    return removed;
}

export function updateExercise(
    id: string,
    field: string,
    value: any
): boolean {
    const updated =
        state.updateExercise(
            id,
            field,
            value
        );

    rerender();

    return updated;
}

export function getExercises(): any[] {
    return state.getExercises();
}

export function getCompletedExercises(): any[] {
    return state.getCompletedExercises();
}

export function replaceExercises(
    exercises: any[]
): void {
    state.replaceExercises(
        exercises
    );

    rerender();
}

export function clear(): void {
    state.clear();
    rerender();
}

export function hasExercises(): boolean {
    return state.hasExercises();
}

export function hasCompletedExercises(): boolean {
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