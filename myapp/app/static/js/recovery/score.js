import { ICONS } from "../icons/icons.js";
import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

function getLevel(score) {
    if (score == null) return "neutral";
    if (score < 40) return "low";
    if (score < 70) return "medium";
    return "high";
}

function miniBar(score) {
    const blocks = Math.round((score ?? 0) / 20);
    const bar = document.createElement("span");
    bar.className = `score-mini-bar ${getLevel(score)}`;
    bar.textContent = "▰".repeat(blocks) + "▱".repeat(5 - blocks);
    return bar;
}

function createRow(iconSvg, label, score, extra = null) {
    const row = document.createElement("div");
    row.className = "score-row";

    const left = document.createElement("div");
    left.className = "score-row-left";

    const icon = document.createElement("span");
    icon.className = "score-icon";
    icon.innerHTML = iconSvg;

    const text = document.createElement("span");
    text.textContent = label;

    left.appendChild(icon);
    left.appendChild(text);

    const right = document.createElement("div");
    right.className = "score-row-right";

    const bar = miniBar(score);
    const value = document.createElement("span");
    value.className = "score-value";
    value.textContent = score ?? "—";

    right.appendChild(bar);
    right.appendChild(value);

    const wrapper = document.createElement("div");
    wrapper.className = "score-row-wrapper";
    wrapper.appendChild(left);
    wrapper.appendChild(right);

    row.appendChild(wrapper);

    if (extra) {
        const extraEl = document.createElement("div");
        extraEl.className = "score-extra";
        extraEl.textContent = extra;
        row.appendChild(extraEl);
    }

    return row;
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

    const header = document.createElement("div");
    header.className = "score-header";

    const icon = document.createElement("span");
    icon.className = "score-header-icon";
    icon.innerHTML = ICONS.heart_pulse;

    const title = document.createElement("span");
    title.className = "score-main-title";
    title.textContent = "Recovery Score";

    header.appendChild(icon);
    header.appendChild(title);

    const total = document.createElement("div");
    total.className = `score-total ${getLevel(snapshot.recovery_score)}`;
    total.textContent = snapshot.recovery_score ?? "—";

    card.appendChild(header);
    card.appendChild(total);

    const divider = document.createElement("div");
    divider.className = "score-divider";
    card.appendChild(divider);

    const content = document.createElement("div");
    content.className = "score-content";

    const sleepExtra = snapshot.sleep_duration_minutes
        ? `${Math.floor(snapshot.sleep_duration_minutes / 60)}h ${snapshot.sleep_duration_minutes % 60}m`
        : null;

    content.appendChild(
        createRow(ICONS.moon, "Sleep", snapshot.sleep_score, sleepExtra)
    );

    content.appendChild(
        createRow(ICONS.habits, "Habits", snapshot.habit_score)
    );

    content.appendChild(
        createRow(ICONS.exercise, "Training", snapshot.training_score)
    );

    content.appendChild(
        createRow(ICONS.energy, "Energy", snapshot.energy_score)
    );

    card.appendChild(content);
    el.appendChild(card);
}
