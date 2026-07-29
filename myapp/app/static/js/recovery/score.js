import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createTitle,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

function smallBar(score) {
    const blocks = Math.round(score / 20);
    const bar = document.createElement("span");
    bar.className = "score-mini-bar";
    bar.textContent = "█".repeat(blocks) + "░".repeat(5 - blocks);
    return bar;
}

function createRow(icon, label, score, extra = null) {
    const row = document.createElement("div");
    row.className = "score-row";

    const left = document.createElement("div");
    left.className = "score-row-left";
    left.innerHTML = `${icon} <span>${label}</span>`;

    const right = document.createElement("div");
    right.className = "score-row-right";

    const bar = smallBar(score ?? 0);
    const value = document.createElement("span");
    value.className = "score-value";
    value.textContent = score ?? "—";

    right.appendChild(bar);
    right.appendChild(value);

    if (extra) {
        const extraEl = document.createElement("div");
        extraEl.className = "score-extra";
        extraEl.textContent = extra;
        row.appendChild(extraEl);
    }

    row.appendChild(left);
    row.appendChild(right);
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

    const title = document.createElement("div");
    title.className = "score-main-title";
    title.textContent = "Recovery";

    const total = document.createElement("div");
    total.className = "score-total";
    total.textContent = snapshot.recovery_score ?? "—";

    card.appendChild(title);
    card.appendChild(total);

    const divider = document.createElement("div");
    divider.className = "score-divider";
    card.appendChild(divider);

    const content = document.createElement("div");
    content.className = "score-content";

    content.appendChild(
        createRow("🌙", "Sleep", snapshot.sleep_score, snapshot.sleep_duration_minutes ? `${Math.floor(snapshot.sleep_duration_minutes/60)}h ${snapshot.sleep_duration_minutes%60}m` : null)
    );

    content.appendChild(
        createRow("🟢", "Habits", snapshot.habit_score)
    );

    content.appendChild(
        createRow("💪", "Training", snapshot.training_score)
    );

    content.appendChild(
        createRow("⚡", "Energy", snapshot.energy_score)
    );

    card.appendChild(content);
    el.appendChild(card);
}
