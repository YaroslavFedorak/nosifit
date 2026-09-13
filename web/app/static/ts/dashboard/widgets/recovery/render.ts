import type { RecoveryState } from "./state";
import { renderSleep } from "./sleep";
import { renderHabits } from "./habits";

function getElement<T extends HTMLElement>(id: string): T | null {
    return document.getElementById(id) as T | null;
}

export function renderLoading(): void {
    const durationEl =
        getElement<HTMLElement>("dashboard-sleep-duration");

    const rangeEl =
        getElement<HTMLElement>("dashboard-sleep-range");

    const qualityEl =
        getElement<HTMLElement>("dashboard-sleep-quality");

    const metaEl =
        getElement<HTMLElement>("dashboard-sleep-meta");

    const habitsEl =
        getElement<HTMLElement>("dashboard-habits");

    const habitsListEl =
        getElement<HTMLElement>("dashboard-habits-list");

    if (durationEl) {
        durationEl.textContent = "Завантаження…";
    }

    if (rangeEl) {
        rangeEl.textContent = "Завантаження даних";
    }

    if (qualityEl) {
        qualityEl.textContent = "—";
    }

    if (metaEl) {
        metaEl.textContent = "";
    }

    if (habitsEl) {
        habitsEl.textContent = "—";
    }

    if (habitsListEl) {
        habitsListEl.textContent = "Завантаження…";
    }
}

export function renderError(): void {
    const durationEl =
        getElement<HTMLElement>("dashboard-sleep-duration");

    const rangeEl =
        getElement<HTMLElement>("dashboard-sleep-range");

    const qualityEl =
        getElement<HTMLElement>("dashboard-sleep-quality");

    const metaEl =
        getElement<HTMLElement>("dashboard-sleep-meta");

    const habitsEl =
        getElement<HTMLElement>("dashboard-habits");

    const habitsListEl =
        getElement<HTMLElement>("dashboard-habits-list");

    if (durationEl) {
        durationEl.textContent = "Помилка";
    }

    if (rangeEl) {
        rangeEl.textContent = "Не вдалося завантажити дані";
    }

    if (qualityEl) {
        qualityEl.textContent = "—";
    }

    if (metaEl) {
        metaEl.textContent = "";
    }

    if (habitsEl) {
        habitsEl.textContent = "—";
    }

    if (habitsListEl) {
        habitsListEl.textContent =
            "Не вдалося завантажити звички";
    }
}

export function renderRecovery(state: RecoveryState): void {
    if (state.loading) {
        renderLoading();
        return;
    }

    if (state.error) {
        renderError();
        return;
    }

    renderSleep(state.snapshot);
    renderHabits(state.snapshot);
}