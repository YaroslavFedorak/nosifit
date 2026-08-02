import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createEmpty,
    createError,
    createLoading
} from "./dom.js";
import { ICONS } from "../icons/icons.js";

function getSleepStatus(minutes) {
    if (!minutes || minutes <= 0) return "Немає даних";
    if (minutes >= 480) return "Відмінний сон";
    if (minutes >= 420) return "Добрий сон";
    if (minutes >= 360) return "Достатній сон";
    return "Недосип";
}

function getScoreColor(score) {
    if (score >= 90) return "var(--nf-green)";
    if (score >= 75) return "var(--nf-blue)";
    if (score >= 60) return "var(--nf-yellow)";
    return "var(--nf-red)";
}

function getRecencyLabel(snapshotDateIso) {
    if (!snapshotDateIso) return "";
    const snap = new Date(snapshotDateIso);
    const today = new Date();
    const s = new Date(snap.getFullYear(), snap.getMonth(), snap.getDate());
    const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diff = Math.round((t - s) / (1000 * 60 * 60 * 24));
    if (diff === 0) return "Останній запис: сьогодні";
    if (diff === 1) return "Останній запис: вчора";
    return `Останній запис: ${snap.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric"
    })}`;
}

export function renderSleepWidget(snapshot, options = {}) {
    const el = document.getElementById("sleep-widget");
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

    if (
        !snapshot ||
        snapshot.sleep_score == null ||
        snapshot.sleep_duration_minutes == null ||
        !snapshot.sleep_start ||
        !snapshot.sleep_end
    ) {
        el.appendChild(createEmpty(RECOVERY_MESSAGES.sleep.empty));
        return;
    }

    const card = createCard("sleep-card");

    const content = document.createElement("div");
    content.className = "sleep-content";

    const durationHours = Math.floor(snapshot.sleep_duration_minutes / 60);
    const durationMinutes = snapshot.sleep_duration_minutes % 60;

    const start = new Date(snapshot.sleep_start);
    const end = new Date(snapshot.sleep_end);

    const startStr = start.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });
    const endStr = end.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });

    const statusText = getSleepStatus(snapshot.sleep_duration_minutes);
    const recencyText = getRecencyLabel(snapshot.date);

    const top = document.createElement("div");
    top.className = "sleep-top";

    const left = document.createElement("div");
    left.className = "sleep-top-left";

    const durationEl = document.createElement("div");
    durationEl.className = "sleep-duration";
    durationEl.textContent = `${durationHours} год ${durationMinutes} хв`;

    const rangeEl = document.createElement("div");
    rangeEl.className = "sleep-range";
    rangeEl.textContent = `${startStr} → ${endStr}`;

    left.appendChild(durationEl);
    left.appendChild(rangeEl);

    const icon = document.createElement("div");
    icon.className = "sleep-icon";
    icon.innerHTML = ICONS.moon;

    top.appendChild(left);
    top.appendChild(icon);

    const barRow = document.createElement("div");
    barRow.className = "sleep-score-row";

    const bar = document.createElement("div");
    bar.className = "sleep-score-bar";

    const fill = document.createElement("div");
    fill.className = "sleep-score-fill";
    fill.style.width = `${snapshot.sleep_score}%`;
    fill.style.background = getScoreColor(snapshot.sleep_score);

    bar.appendChild(fill);

    const scoreLabel = document.createElement("div");
    scoreLabel.className = "sleep-score-label";
    scoreLabel.textContent = `${snapshot.sleep_score}%`;

    barRow.appendChild(bar);
    barRow.appendChild(scoreLabel);

    const bottom = document.createElement("div");
    bottom.className = "sleep-bottom";

    const statusEl = document.createElement("div");
    statusEl.className = "sleep-status";
    statusEl.textContent = statusText;

    const metaEl = document.createElement("div");
    metaEl.className = "sleep-meta";
    metaEl.textContent = recencyText;

    bottom.appendChild(statusEl);
    bottom.appendChild(metaEl);

    content.appendChild(top);
    content.appendChild(barRow);
    content.appendChild(bottom);

    card.appendChild(content);
    el.appendChild(card);
}
