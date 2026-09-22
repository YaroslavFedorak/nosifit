import { RECOVERY_MESSAGES } from "./messages.js";
import { RECOVERY_ICONS } from "../icons/recovery.js";
import { TRAINING_ICONS } from "../icons/training.js";
import { clearElement, createCard, createLoading, createError, createEmpty } from "./dom.js";
const PRIORITY_ORDER = {
    high: 1,
    medium: 2,
    low: 3
};
const TRAINING_ICON_MAP = TRAINING_ICONS;
const RECOVERY_ICON_MAP = RECOVERY_ICONS;
const ICON_MAP = {
    sleep: "moon",
    hydration: "water",
    recovery: "rest",
    activity: "exercise",
    stress: "caution",
    nutrition: "plan",
    massage: "hand_heart",
    habit: "calendar_cog",
    exercise: "exercise",
    muscle: "exercise"
};
const MAX_RECOMMENDATIONS = 4;
function getIcon(name) {
    if (TRAINING_ICON_MAP[name]) {
        return TRAINING_ICON_MAP[name];
    }
    if (RECOVERY_ICON_MAP[name]) {
        return RECOVERY_ICON_MAP[name];
    }
    return "";
}
function sortRecommendations(list) {
    return [...list].sort((a, b) => (PRIORITY_ORDER[a.priority || ""] ?? 99) -
        (PRIORITY_ORDER[b.priority || ""] ?? 99));
}
function createRecommendation(rec) {
    const item = document.createElement("div");
    item.className =
        "rec-item";
    const icon = document.createElement("div");
    icon.className =
        "rec-icon";
    const iconName = ICON_MAP[rec.type || ""] || "rest";
    icon.innerHTML =
        getIcon(iconName);
    const title = document.createElement("div");
    title.className =
        "rec-title";
    title.textContent =
        rec.text || "";
    item.appendChild(icon);
    item.appendChild(title);
    return item;
}
function normalizeRecommendations(data) {
    const raw = data?.recommendations;
    if (Array.isArray(raw)) {
        return raw.filter((rec) => Boolean(rec?.text &&
            rec.text.trim() !== ""));
    }
    if (raw &&
        typeof raw === "object" &&
        Array.isArray(raw.items)) {
        return raw.items.filter((rec) => Boolean(rec?.text &&
            rec.text.trim() !== ""));
    }
    return [];
}
export function renderRecommendationsWidget(data, options = {}) {
    const el = document.getElementById("recommendations-widget");
    if (!el) {
        return;
    }
    clearElement(el);
    if (options.loading) {
        el.appendChild(createLoading(RECOVERY_MESSAGES.loading));
        return;
    }
    if (options.error) {
        el.appendChild(createError(RECOVERY_MESSAGES.error));
        return;
    }
    const recommendations = normalizeRecommendations(data);
    if (recommendations.length === 0) {
        el.appendChild(createEmpty("Поки все добре"));
        return;
    }
    const card = createCard("recommendations-card");
    const content = document.createElement("div");
    content.className =
        "rec-grid";
    sortRecommendations(recommendations)
        .slice(0, MAX_RECOMMENDATIONS)
        .forEach((rec) => {
        content.appendChild(createRecommendation(rec));
    });
    card.appendChild(content);
    el.appendChild(card);
}
