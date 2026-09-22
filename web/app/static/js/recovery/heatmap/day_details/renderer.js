import { createMiniCard } from "./modal.js";
function formatScore(value) {
    return value == null
        ? "—"
        : String(Math.round(value));
}
function getStatus(value) {
    if (value == null) {
        return "Немає даних";
    }
    if (value >= 80) {
        return "Добре";
    }
    if (value >= 60) {
        return "Нормально";
    }
    if (value >= 40) {
        return "Увага";
    }
    return "Низько";
}
function getBarFill(value) {
    if (value == null) {
        return 0;
    }
    return Math.max(0, Math.min(100, value));
}
export function createSummaryCard(name, value, status, barFill = 0) {
    return createMiniCard(name, value, status, barFill);
}
export function createDailySummary(data) {
    const wrapper = document.createElement("div");
    wrapper.className =
        "rc-daily-summary";
    const recoveryScore = data.recovery?.score ?? null;
    const sleepScore = data.sleep?.quality_score ?? null;
    const trainingLoad = data.training?.load ?? null;
    const habitsScore = data.habits?.score ?? null;
    wrapper.appendChild(createSummaryCard("Відновлення", formatScore(recoveryScore), getStatus(recoveryScore), getBarFill(recoveryScore)));
    wrapper.appendChild(createSummaryCard("Сон", formatScore(sleepScore), getStatus(sleepScore), getBarFill(sleepScore)));
    wrapper.appendChild(createSummaryCard("Навантаження", trainingLoad == null
        ? "—"
        : Math.round(trainingLoad), trainingLoad == null
        ? "Немає даних"
        : "Тренування", trainingLoad == null
        ? 0
        : Math.min(100, trainingLoad)));
    wrapper.appendChild(createSummaryCard("Звички", formatScore(habitsScore), getStatus(habitsScore), getBarFill(habitsScore)));
    return wrapper;
}
export function createHabitsGrid(habits) {
    const grid = document.createElement("div");
    grid.className =
        "rc-habits-grid";
    habits.forEach((habit) => {
        grid.appendChild(createHabitRow(habit));
    });
    return grid;
}
export function createHabitRow(habit) {
    const row = document.createElement("div");
    row.className =
        "rc-habit-row";
    if (habit.completed) {
        row.classList.add("completed");
    }
    const icon = document.createElement("div");
    icon.className =
        "rc-habit-icon";
    icon.textContent =
        habit.icon || "✓";
    const content = document.createElement("div");
    content.className =
        "rc-habit-content";
    const title = document.createElement("div");
    title.className =
        "rc-habit-name";
    title.textContent =
        habit.name || "Звичка";
    const category = document.createElement("div");
    category.className =
        "rc-habit-category";
    category.textContent =
        habit.category || "";
    content.appendChild(title);
    content.appendChild(category);
    const status = document.createElement("div");
    status.className =
        "rc-habit-status";
    status.textContent =
        habit.completed
            ? "Виконано"
            : "Не виконано";
    row.appendChild(icon);
    row.appendChild(content);
    row.appendChild(status);
    return row;
}
export function createRecommendationRow(recommendation) {
    const row = document.createElement("div");
    row.className =
        "rc-recommendation-row";
    const icon = document.createElement("div");
    icon.className =
        "rc-recommendation-icon";
    icon.textContent =
        recommendation.icon || "•";
    const content = document.createElement("div");
    content.className =
        "rc-recommendation-text";
    content.textContent =
        recommendation.text || "";
    if (recommendation.priority) {
        row.dataset.priority =
            recommendation.priority;
    }
    row.appendChild(icon);
    row.appendChild(content);
    return row;
}
