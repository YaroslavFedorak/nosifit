import {
    RECOVERY_ICONS
} from "../icons/recovery.js";

import {
    TRAINING_ICONS
} from "../icons/training.js";

import {
    TRACKER_ICONS
} from "../icons/tracker.js";

import {
    recovery_t
} from "../i18n/index.js";

import {
    clearElement,
    createCard,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

import type {
    RecoveryRecommendation,
    RecoveryRecommendationsResponse
} from "./api.js";

export type Recommendation =
    RecoveryRecommendation;

export type RecommendationsData =
    RecoveryRecommendationsResponse;

interface RenderOptions {
    loading?: boolean;
    error?: string | null;
}

const PRIORITY_ORDER: Record<string, number> = {
    high: 1,
    medium: 2,
    low: 3
};

const TRAINING_ICON_MAP =
    TRAINING_ICONS as Record<string, string>;

const RECOVERY_ICON_MAP =
    RECOVERY_ICONS as Record<string, string>;

const TRACKER_ICON_MAP =
    TRACKER_ICONS as Record<string, string>;

const ICON_MAP: Record<string, string> = {
    sleep: "moon",
    hydration: "water",
    recovery: "rest",
    activity: "exercise",
    stress: "caution",
    nutrition: "plan",
    massage: "hand_heart",
    habit: "calendar_cog",
    exercise: "exercise",
    muscle: "exercise",
    training: "exercise"
};

const MAX_RECOMMENDATIONS = 4;

const MUSCLE_KEYS: Record<string, string> = {
    chest: "chest",
    back: "back",
    shoulders: "shoulders",
    biceps: "biceps",
    triceps: "triceps",
    forearms: "forearms",
    "upper-back": "upper_back",
    upper_back: "upper_back",
    traps: "traps",
    quads: "quads",
    quadriceps: "quadriceps",
    hamstrings: "hamstrings",
    glutes: "glutes",
    calves: "calves",
    core: "core",
    abs: "abs"
};

function getIcon(
    name: string
): string {
    return (
        TRAINING_ICON_MAP[name] ||
        RECOVERY_ICON_MAP[name] ||
        TRACKER_ICON_MAP[name] ||
        ""
    );
}

function getMuscleName(
    muscle?: string | null
): string {
    if (!muscle) {
        return "";
    }

    const normalized =
        muscle
            .trim()
            .toLowerCase()
            .replace(/-/g, "_");

    const key =
        MUSCLE_KEYS[normalized];

    if (!key) {
        return muscle;
    }

    return recovery_t(
        `muscles.${key}`
    );
}

function getRecommendationKey(
    recommendation: Recommendation
): string | null {
    const id =
        recommendation.id?.trim();

    if (!id) {
        return null;
    }

    if (id.startsWith("rest_")) {
        return "rest_muscle";
    }

    if (id.startsWith("train_")) {
        return "train_muscle";
    }

    return id;
}

function getRecommendationParams(
    recommendation: Recommendation
): Record<string, string | number> {
    return {
        muscle: getMuscleName(
            recommendation.muscle
        )
    };
}

function getRecommendationText(
    recommendation: Recommendation
): string {
    const key =
        getRecommendationKey(
            recommendation
        );

    if (!key) {
        return (
            recommendation.text ||
            recommendation.description ||
            recommendation.message ||
            ""
        );
    }

    const translation =
        recovery_t(
            `recommendations.items.${key}.text`,
            getRecommendationParams(
                recommendation
            )
        );

    if (
        translation !==
        `recommendations.items.${key}.text`
    ) {
        return translation;
    }

    return (
        recommendation.text ||
        recommendation.description ||
        recommendation.message ||
        ""
    );
}

function getRecommendationTitle(
    recommendation: Recommendation
): string {
    const key =
        getRecommendationKey(
            recommendation
        );

    if (!key) {
        return (
            recommendation.title ||
            ""
        );
    }

    const translation =
        recovery_t(
            `recommendations.items.${key}.title`,
            getRecommendationParams(
                recommendation
            )
        );

    if (
        translation ===
        `recommendations.items.${key}.title`
    ) {
        return (
            recommendation.title ||
            ""
        );
    }

    return translation;
}

function sortRecommendations(
    list: Recommendation[]
): Recommendation[] {
    return [...list].sort(
        (a, b) =>
            (
                PRIORITY_ORDER[
                    a.priority || ""
                ] ?? 99
            ) -
            (
                PRIORITY_ORDER[
                    b.priority || ""
                ] ?? 99
            )
    );
}

function createRecommendation(
    recommendation: Recommendation
): HTMLDivElement {
    const item =
        document.createElement("div");

    item.className =
        "rec-item";

    const icon =
        document.createElement("div");

    icon.className =
        "rec-icon";

    const iconName =
        ICON_MAP[
            recommendation.type || ""
        ] || "rest";

    icon.innerHTML =
        getIcon(iconName);

    const body =
        document.createElement("div");

    body.className =
        "rec-body";

    const titleText =
        getRecommendationTitle(
            recommendation
        );

    const text =
        getRecommendationText(
            recommendation
        );

    if (titleText) {
        const title =
            document.createElement("div");

        title.className =
            "rec-title";

        title.textContent =
            titleText;

        body.appendChild(title);
    }

    if (text) {
        const textElement =
            document.createElement("div");

        textElement.className =
            "rec-text";

        textElement.textContent =
            text;

        body.appendChild(textElement);
    }

    if (!titleText && !text) {
        const fallback =
            document.createElement("div");

        fallback.className =
            "rec-text";

        fallback.textContent =
            recovery_t(
                "recommendations.fallback"
            );

        body.appendChild(fallback);
    }

    item.appendChild(icon);
    item.appendChild(body);

    return item;
}

function normalizeRecommendations(
    data: RecommendationsData | null
): Recommendation[] {
    if (!data?.recommendations) {
        return [];
    }

    if (
        Array.isArray(
            data.recommendations
        )
    ) {
        return data.recommendations.filter(
            recommendation =>
                Boolean(
                    recommendation &&
                    recommendation.id
                )
        );
    }

    const items =
        data.recommendations.items;

    if (!Array.isArray(items)) {
        return [];
    }

    return items.filter(
        recommendation =>
            Boolean(
                recommendation &&
                recommendation.id
            )
    );
}

export function renderRecommendationsWidget(
    data: RecommendationsData | null,
    options: RenderOptions = {}
): void {
    const element =
        document.getElementById(
            "recommendations-widget"
        );

    if (!element) {
        return;
    }

    clearElement(element);

    if (options.loading) {
        element.appendChild(
            createLoading(
                recovery_t("loading")
            )
        );

        return;
    }

    if (options.error) {
        element.appendChild(
            createError(
                recovery_t("error")
            )
        );

        return;
    }

    const recommendations =
        normalizeRecommendations(data);

    if (recommendations.length === 0) {
        element.appendChild(
            createEmpty(
                recovery_t(
                    "recommendations.empty"
                )
            )
        );

        return;
    }

    const card =
        createCard(
            "recommendations-card"
        );

    const content =
        document.createElement("div");

    content.className =
        "rec-grid";

    sortRecommendations(
        recommendations
    )
        .slice(
            0,
            MAX_RECOMMENDATIONS
        )
        .forEach(
            recommendation => {
                content.appendChild(
                    createRecommendation(
                        recommendation
                    )
                );
            }
        );

    card.appendChild(content);
    element.appendChild(card);
}