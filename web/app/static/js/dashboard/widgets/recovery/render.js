import { renderHabitsWidget } from "./habits.js";
import { renderSleepWidget } from "./sleep.js";
export function renderRecoveryWidget(state) {
    renderSleepWidget(state.snapshot);
    renderHabitsWidget(state.snapshot);
}
