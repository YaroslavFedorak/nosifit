import { renderSleep } from "./sleep";
import { renderHabits } from "./habits";
function getElement(id) {
    return document.getElementById(id);
}
export function renderLoading() {
    const durationEl = getElement("dashboard-sleep-duration");
    const rangeEl = getElement("dashboard-sleep-range");
    const qualityEl = getElement("dashboard-sleep-quality");
    const metaEl = getElement("dashboard-sleep-meta");
    const habitsEl = getElement("dashboard-habits");
    const habitsListEl = getElement("dashboard-habits-list");
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
export function renderError() {
    const durationEl = getElement("dashboard-sleep-duration");
    const rangeEl = getElement("dashboard-sleep-range");
    const qualityEl = getElement("dashboard-sleep-quality");
    const metaEl = getElement("dashboard-sleep-meta");
    const habitsEl = getElement("dashboard-habits");
    const habitsListEl = getElement("dashboard-habits-list");
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
export function renderRecovery(state) {
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
