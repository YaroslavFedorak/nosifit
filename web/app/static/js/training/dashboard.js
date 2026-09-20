export function renderCurrentDate() {
    const element = document.getElementById("current-date");
    if (!element) {
        return;
    }
    const date = new Date();
    element.textContent =
        date.toLocaleDateString("uk-UA", {
            weekday: "long",
            day: "numeric",
            month: "long"
        });
}
export function renderAnalytics(data) {
    const performance = data.performance || {};
    const recovery = data.recovery || {};
    const performanceElement = document.getElementById("tr-performance");
    const recoveryElement = document.getElementById("tr-recovery");
    if (performanceElement) {
        const averagePerformance = (performance.pushups || 0) +
            (performance.squats || 0) +
            (performance.situps || 0);
        performanceElement.textContent =
            averagePerformance
                ? String(Math.round(averagePerformance / 3))
                : "—";
    }
    if (recoveryElement) {
        const averageRecovery = (recovery.sleep || 0) -
            (recovery.stress || 0) -
            (recovery.soreness || 0);
        recoveryElement.textContent =
            averageRecovery
                ? String(Math.round(averageRecovery))
                : "—";
    }
}
export function renderStrengthTestResults(performance) {
    if (!performance) {
        return;
    }
    const pushups = document.getElementById("st-result-pushups");
    const squats = document.getElementById("st-result-squats");
    const situps = document.getElementById("st-result-situps");
    if (pushups) {
        pushups.textContent =
            String(performance.pushups ?? "—");
    }
    if (squats) {
        squats.textContent =
            String(performance.squats ?? "—");
    }
    if (situps) {
        situps.textContent =
            String(performance.situps ?? "—");
    }
}
