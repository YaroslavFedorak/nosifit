import { ICONS } from "../../../icons/index.js";
import { createMiniCard } from "./day_card.js";
const ICON_ALIASES = {
    recovery: "rest",
    activity: "mobility",
    sleep: "bed",
    nutrition: "meal",
    water: "droplet",
    hydration: "droplet",
    electrolyte: "electrolytes",
    electrolytes: "electrolytes",
    stretch: "stretch",
    mobility: "mobility",
    foam_roll: "foam_roll",
    breathing: "breathing",
    meditation: "meditation",
    journal: "journal",
    rest: "rest",
    massage: "massage",
    deload: "deload"
};
const RECOMMENDATION_ICONS = {
    recovery: "rest",
    habit: "rest",
    training: "mobility",
    sleep: "bed",
    nutrition: "meal",
    activity: "mobility"
};
function getIcon(key) {
    if (!key) {
        return "";
    }
    const resolvedKey = ICON_ALIASES[key] ?? key;
    if (resolvedKey in ICONS) {
        return ICONS[resolvedKey];
    }
    return "";
}
function getRecommendationIcon(recommendation) {
    if (recommendation.icon) {
        const icon = getIcon(recommendation.icon);
        if (icon) {
            return icon;
        }
    }
    if (recommendation.type) {
        const iconKey = RECOMMENDATION_ICONS[recommendation.type];
        if (iconKey) {
            return ICONS[iconKey];
        }
    }
    return ICONS.rest;
}
function formatScore(value) {
    if (value == null ||
        !Number.isFinite(Number(value))) {
        return "—";
    }
    return String(Math.round(Number(value)));
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
    if (value == null ||
        !Number.isFinite(Number(value))) {
        return 0;
    }
    return Math.max(0, Math.min(100, Number(value)));
}
export function createSummaryCard(name, value, status, barFill = 0) {
    return createMiniCard(name, value, status, barFill);
}
export function createDailySummary(data) {
    const wrapper = document.createElement("div");
    wrapper.className =
        "rc-daily-summary";
    const recovery = data.recovery?.score ??
        null;
    const sleep = data.sleep?.quality_score ??
        null;
    const training = data.training?.load ??
        null;
    const habits = data.habits?.score ??
        null;
    wrapper.appendChild(createSummaryCard("Відновлення", formatScore(recovery), getStatus(recovery), getBarFill(recovery)));
    wrapper.appendChild(createSummaryCard("Сон", formatScore(sleep), getStatus(sleep), getBarFill(sleep)));
    wrapper.appendChild(createSummaryCard("Навантаження", training == null
        ? "—"
        : Math.round(training), training == null
        ? "Немає даних"
        : "Тренування", training == null
        ? 0
        : Math.min(100, Math.max(0, training))));
    wrapper.appendChild(createSummaryCard("Звички", formatScore(habits), getStatus(habits), getBarFill(habits)));
    return wrapper;
}
export function createHabitsGrid(habits) {
    const grid = document.createElement("div");
    grid.className =
        "rc-habits-grid";
    habits.forEach(habit => {
        grid.appendChild(createHabitRow(habit));
    });
    if (habits.length === 0) {
        const empty = document.createElement("div");
        empty.className =
            "rc-empty-state";
        empty.textContent =
            "За цей день звичок немає";
        grid.appendChild(empty);
    }
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
    icon.setAttribute("aria-hidden", "true");
    const iconMarkup = getIcon(habit.icon);
    if (iconMarkup) {
        icon.innerHTML =
            iconMarkup;
    }
    const content = document.createElement("div");
    content.className =
        "rc-habit-meta";
    const name = document.createElement("div");
    name.className =
        "rc-habit-name";
    name.textContent =
        habit.name ||
            "Звичка";
    content.appendChild(name);
    if (habit.category) {
        const category = document.createElement("div");
        category.className =
            "rc-habit-category";
        category.textContent =
            habit.category;
        content.appendChild(category);
    }
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
        "rc-recommendation";
    if (recommendation.priority) {
        row.dataset.priority =
            String(recommendation.priority);
    }
    const icon = document.createElement("div");
    icon.className =
        "rc-rec-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML =
        getRecommendationIcon(recommendation);
    const body = document.createElement("div");
    body.className =
        "rc-rec-body";
    const title = recommendation.title ||
        "";
    const text = recommendation.text ||
        recommendation.description ||
        recommendation.message ||
        "";
    if (title) {
        const titleElement = document.createElement("div");
        titleElement.className =
            "rc-rec-title";
        titleElement.textContent =
            title;
        body.appendChild(titleElement);
    }
    if (text) {
        const textElement = document.createElement("div");
        textElement.className =
            "rc-rec-text";
        textElement.textContent =
            text;
        body.appendChild(textElement);
    }
    if (!title &&
        !text) {
        const empty = document.createElement("div");
        empty.className =
            "rc-rec-text";
        empty.textContent =
            "Рекомендація";
        body.appendChild(empty);
    }
    row.appendChild(icon);
    row.appendChild(body);
    return row;
}
