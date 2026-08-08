import { ICONS } from "../icons/index.js";
import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

function normalize(v) {
    const num = Number(v);
    if (Number.isNaN(num)) return 0;
    if (num <= 5) return num * 20;
    return Math.max(0, Math.min(num, 100));
}

function getLevel(v) {
    const n = normalize(v);
    if (n < 40) return "low";
    if (n < 70) return "medium";
    return "high";
}

function getStatus(score) {
    const n = normalize(score);
    if (n < 40) return "Потребує уваги";
    if (n < 70) return "Середній стан";
    if (n < 85) return "Добре";
    return "Відмінно";
}

function createBar(score) {
    const bar = document.createElement("div");
    bar.className = "score-bar";

    const normalized = normalize(score);
    const filled = Math.round(normalized / 20);
    const level = getLevel(score);

    for (let i = 0; i < 5; i++) {
        const seg = document.createElement("div");
        seg.className = "score-segment";
        if (i < filled) seg.classList.add("filled", level);
        bar.appendChild(seg);
    }

    return bar;
}

function createItem(iconSvg, label, score) {
    const item = document.createElement("div");
    item.className = "score-item";

    const top = document.createElement("div");
    top.className = "score-top";

    const left = document.createElement("div");
    left.className = "score-left";

    const icon = document.createElement("span");
    icon.className = "score-icon";
    icon.innerHTML = iconSvg;

    const text = document.createElement("span");
    text.className = "score-label";
    text.textContent = label;

    left.appendChild(icon);
    left.appendChild(text);

    const value = document.createElement("span");
    value.className = "score-value";
    value.textContent = `${normalize(score)}%`;

    top.appendChild(left);
    top.appendChild(value);

    const bar = createBar(score);

    const status = document.createElement("div");
    status.className = "score-status";
    status.textContent = getStatus(score);

    item.appendChild(top);
    item.appendChild(bar);
    item.appendChild(status);

    return item;
}

export function renderScoreWidget(snapshot, options = {}) {
    const el = document.getElementById("score-widget");
    if (!el) return;

    clearElement(el);

    if (options.loading) {
        el.appendChild(createLoading(RECOVERY_MESSAGES.loading));
        return;
    }

    if (options.error) {
        el.appendChild(createError(RECOVERY_MESSAGES.error));
        return;
    }

    if (!snapshot) {
        el.appendChild(createEmpty(RECOVERY_MESSAGES.score.empty));
        return;
    }

    const card = createCard("score-card");

    card.appendChild(createItem(ICONS.moon, "Сон", snapshot.sleep_score));
    card.appendChild(createItem(ICONS.exercise, "Тренування", snapshot.training_score));
    card.appendChild(createItem(ICONS.zap, "Енергія", snapshot.energy_score));
    card.appendChild(createItem(ICONS.calendar_cog, "Звички", snapshot.habit_score));

    el.appendChild(card);
}
