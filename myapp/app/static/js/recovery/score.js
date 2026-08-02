import { ICONS } from "../icons/icons.js";
import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

function normalize(v) {
    if (typeof v !== "number") return 0;
    return Math.max(0, Math.min(v, 100));
}

function getLevel(v) {
    const n = normalize(v);
    if (n < 40) return "low";
    if (n < 70) return "medium";
    return "high";
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

        const tooltip = document.createElement("div");
        tooltip.className = "score-tooltip";
        tooltip.textContent = `${normalized}%`;

        seg.appendChild(tooltip);
        bar.appendChild(seg);
    }

    return bar;
}

function createItem(iconSvg, label, score) {
    const item = document.createElement("div");
    item.className = "score-item";

    const top = document.createElement("div");
    top.className = "score-top";

    const icon = document.createElement("span");
    icon.className = "score-icon";
    icon.innerHTML = iconSvg;

    const text = document.createElement("span");
    text.className = "score-label";
    text.textContent = label;

    top.appendChild(icon);
    top.appendChild(text);

    const bar = createBar(score);

    item.appendChild(top);
    item.appendChild(bar);

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

    card.appendChild(createItem(ICONS.moon, "Sleep", snapshot.sleep_score));
    card.appendChild(createItem(ICONS.habits, "Habits", snapshot.habit_score));
    card.appendChild(createItem(ICONS.exercise, "Training", snapshot.training_score));
    card.appendChild(createItem(ICONS.energy, "Energy", snapshot.energy_score));

    el.appendChild(card);
}
