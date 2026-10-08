import { translate } from "../../i18n/loader.js";
const ICONS = {
    training: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="M17.596 12.768a2 2 0 1 0 2.829-2.829l-1.768-1.767a2 2 0 0 0 2.828-2.829l-2.828-2.828a2 2 0 0 0-2.829 2.828l-1.767-1.768a2 2 0 1 0-2.829 2.829z"/>
            <path d="m2.5 21.5 1.4-1.4"/>
            <path d="m20.1 3.9 1.4-1.4"/>
            <path d="M5.343 21.485a2 2 0 1 0 2.829-2.828l1.767 1.768a2 2 0 1 0 2.829-2.829l-6.364-6.364a2 2 0 1 0-2.829 2.829l1.768 1.767a2 2 0 1 0-2.828 2.829z"/>
            <path d="m9.6 14.4 4.8-4.8"/>
        </svg>
    `,
    recovery: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="M19.414 14.414C21 12.828 22 11.5 22 9.5a5.5 5.5 0 0 0-9.591-3.676.6.6 0 0 1-.818.001A5.5 5.5 0 0 0 2 9.5c0 2.3 1.5 4 3 5.5l5.535 5.362a2 2 0 0 0 2.879.052 2.12 2.12 0 0 0-.004-3 2.124 2.124 0 1 0 3-3 2.124 2.124 0 1 0 3.004 0 2 2 0 0 0 0-2.828l-1.881-1.882a2.41 2.41 0 0 0-3.409 0l-1.71 1.71a2 2 0 0 1-2.828 0 2 2 0 0 1 0-2.828l2.823-2.762"/>
        </svg>
    `,
    nutrition: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="M22 5V2l-5.89 5.89"/>
            <circle cx="16.6" cy="15.89" r="3"/>
            <circle cx="8.11" cy="7.4" r="3"/>
            <circle cx="12.35" cy="11.65" r="3"/>
            <circle cx="13.91" cy="5.85" r="3"/>
            <circle cx="18.15" cy="10.09" r="3"/>
            <circle cx="6.56" cy="13.2" r="3"/>
            <circle cx="10.8" cy="17.44" r="3"/>
            <circle cx="5" cy="19" r="3"/>
        </svg>
    `
};
const CATEGORY_LABELS = {
    training: "recommendations.categories.training",
    recovery: "recommendations.categories.recovery",
    nutrition: "recommendations.categories.nutrition"
};
const CATEGORY_EMPTY_TEXT = {
    training: "recommendations.emptyCategory",
    recovery: "recommendations.emptyCategory",
    nutrition: "recommendations.emptyCategory"
};
const TECHNICAL_TITLES = new Set([
    "",
    "training",
    "recovery",
    "nutrition"
]);
function createElement(tag, className) {
    const element = document.createElement(tag);
    element.className =
        className;
    return element;
}
const RECOMMENDATION_NAMESPACES = [
    "dashboard",
    "nutrition",
    "recovery",
    "training",
];
function translateRecommendation(key, fallback, params = {}) {
    if (!key) {
        return fallback;
    }
    // Recommendations come from several modules; their keys live in that
    // module's namespace (e.g. nutrition recommendations in "nutrition").
    for (const namespace of RECOMMENDATION_NAMESPACES) {
        const translated = translate(namespace, key, params);
        if (translated !== key) {
            return translated;
        }
    }
    return fallback || key;
}
function translateExercise(key, fallback) {
    const normalizedKey = key.trim();
    if (!normalizedKey) {
        return fallback;
    }
    const translated = translate("exercises", normalizedKey);
    if (typeof translated === "string" &&
        translated !==
            normalizedKey) {
        return translated;
    }
    return fallback;
}
function getCategoryLabel(category) {
    return translate("dashboard", CATEGORY_LABELS[category]);
}
function getCategoryEmptyText(category) {
    return translate("dashboard", CATEGORY_EMPTY_TEXT[category]);
}
function getRecommendationTitle(recommendation, category) {
    const title = recommendation.title?.trim();
    if (recommendation.title_key) {
        return translateRecommendation(recommendation.title_key, title || "", recommendation.params ?? {});
    }
    if (title &&
        !TECHNICAL_TITLES.has(title.toLowerCase()) &&
        title.toLowerCase() !==
            category) {
        if (category ===
            "training") {
            return translateExercise(recommendation.slug
                ? `${recommendation.slug}.name`
                : title, title);
        }
        return title;
    }
    const description = recommendation.description?.trim();
    if (recommendation.description_key) {
        return translateRecommendation(recommendation.description_key, description || "", recommendation.params ?? {});
    }
    if (description) {
        return description;
    }
    const reason = recommendation.reason?.trim();
    if (recommendation.reason_key) {
        return translateRecommendation(recommendation.reason_key, reason || "", recommendation.params ?? {});
    }
    if (reason) {
        return reason;
    }
    return getCategoryEmptyText(category);
}
function getRecommendationDescription(recommendation, displayTitle) {
    const description = recommendation.description?.trim();
    if (recommendation.description_key) {
        const translated = translateRecommendation(recommendation.description_key, description || "", recommendation.params ?? {});
        if (translated !== displayTitle) {
            return translated;
        }
    }
    else if (description &&
        description !== displayTitle) {
        return description;
    }
    const reason = recommendation.reason?.trim();
    if (recommendation.reason_key) {
        const translated = translateRecommendation(recommendation.reason_key, reason || "", recommendation.params ?? {});
        if (translated !== displayTitle) {
            return translated;
        }
    }
    else if (reason &&
        reason !== displayTitle) {
        return reason;
    }
    return "";
}
function createCategoryCard(category, recommendation) {
    const card = createElement("div", `db-recommendation-category db-recommendation-category-${category}`);
    const inner = createElement("div", "db-recommendation-category-inner");
    const icon = createElement("div", "db-recommendation-category-icon");
    icon.innerHTML =
        ICONS[category];
    const body = createElement("div", "db-recommendation-category-body");
    const label = createElement("div", "db-recommendation-category-label");
    label.textContent =
        getCategoryLabel(category);
    const title = createElement("div", "db-recommendation-category-title");
    title.textContent =
        recommendation
            ? getRecommendationTitle(recommendation, category)
            : getCategoryEmptyText(category);
    body.appendChild(label);
    body.appendChild(title);
    inner.appendChild(icon);
    inner.appendChild(body);
    card.appendChild(inner);
    return card;
}
function getDailyCategory(recommendation) {
    if (recommendation.category ===
        "training") {
        return "training";
    }
    if (recommendation.category ===
        "nutrition") {
        return "nutrition";
    }
    return "recovery";
}
function createDailyRecommendation(recommendation) {
    const daily = createElement("div", "db-recommendation-daily");
    if (!recommendation) {
        const empty = createElement("div", "db-recommendations-empty");
        empty.textContent =
            translate("dashboard", "recommendations.emptyDaily");
        daily.appendChild(empty);
        return daily;
    }
    const category = getDailyCategory(recommendation);
    const inner = createElement("div", "db-recommendation-daily-inner");
    const icon = createElement("div", `db-recommendation-daily-icon db-recommendation-daily-icon-${category}`);
    icon.innerHTML =
        ICONS[category];
    const body = createElement("div", "db-recommendation-daily-body");
    const label = createElement("div", "db-recommendation-daily-label");
    label.textContent =
        translate("dashboard", "recommendations.dailyTitle");
    const title = createElement("div", "db-recommendation-daily-title");
    const displayTitle = getRecommendationTitle(recommendation, category);
    title.textContent =
        displayTitle;
    const description = createElement("div", "db-recommendation-daily-description");
    const recommendationDescription = getRecommendationDescription(recommendation, displayTitle);
    if (recommendationDescription) {
        description.textContent =
            recommendationDescription;
        body.appendChild(description);
    }
    const source = createElement("div", "db-recommendation-daily-source");
    source.textContent =
        getCategoryLabel(category);
    body.appendChild(label);
    body.appendChild(title);
    inner.appendChild(icon);
    inner.appendChild(body);
    inner.appendChild(source);
    daily.appendChild(inner);
    return daily;
}
function isDashboardRecommendations(value) {
    if (value === null ||
        typeof value !== "object" ||
        Array.isArray(value)) {
        return false;
    }
    const data = value;
    if (!("daily" in data) ||
        !("categories" in data)) {
        return false;
    }
    if (data.categories === null ||
        typeof data.categories !== "object" ||
        Array.isArray(data.categories)) {
        return false;
    }
    return true;
}
export function renderRecommendations(container, recommendations) {
    if (!container) {
        return;
    }
    container.innerHTML = "";
    if (!isDashboardRecommendations(recommendations)) {
        const empty = createElement("div", "db-recommendations-empty");
        empty.textContent =
            translate("dashboard", "recommendations.empty");
        container.appendChild(empty);
        return;
    }
    const categories = createElement("div", "db-recommendation-categories");
    categories.appendChild(createCategoryCard("training", recommendations.categories.training));
    categories.appendChild(createCategoryCard("recovery", recommendations.categories.recovery));
    categories.appendChild(createCategoryCard("nutrition", recommendations.categories.nutrition));
    container.appendChild(categories);
    container.appendChild(createDailyRecommendation(recommendations.daily));
}
