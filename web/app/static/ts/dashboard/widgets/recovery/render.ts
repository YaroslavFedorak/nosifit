import {
    renderHabitsWidget
} from "./habits.js";

import {
    renderSleepWidget
} from "./sleep.js";

import type {
    RecoveryState
} from "./state.js";

export function renderRecoveryWidget(
    state: RecoveryState
): void {
    renderSleepWidget(
        state.snapshot
    );

    renderHabitsWidget(
        state.snapshot
    );
}