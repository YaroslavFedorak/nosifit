import { ICONS } from "../icons/index.js";

import {
    t
} from "../i18n/index.js";

type RecommendationItem = {
    exercise?: string;
    reasons?: string[];
    score?: number;
};

type MuscleData = {
    weak?: string[];
    balanced?: string[];
    overloaded?: string[];
    totals?: Record<string, number>;
    balance_ratio?: Record<string, number>;
    message?: string;
};

export type RecommendationsData = {
    load?: unknown;
    muscles?: MuscleData;
    patterns?: unknown;
    progression?: unknown;
    recovery?: unknown;
    diversity?: unknown;
    frequency?: unknown;
    recommended_exercises?: RecommendationItem[];
    summary?: string;
    [key: string]: unknown;
};

function safeArray<T>(
    value: T[] | T | null | undefined
): T[] {
    if (Array.isArray(value)) {
        return value;
    }

    if (
        value === null ||
        value === undefined
    ) {
        return [];
    }

    return [value];
}

function capitalize(
    value: unknown
): string {
    const text =
        String(
            value || ""
        ).trim();

    if (!text) {
        return "";
    }

    return (
        text.charAt(0).toUpperCase() +
        text.slice(1)
    );
}

function translateMuscle(
    value: unknown
): string {
    const key =
        String(
            value || ""
        )
            .trim()
            .toLowerCase();

    const translationKey =
        key === "hip-flexors"
            ? "muscles.hipFlexors"
            : key === "lower-back"
                ? "muscles.lowerBack"
                : `muscles.${key}`;

    const translated =
        t(translationKey);

    return translated !== translationKey
        ? translated
        : capitalize(value);
}

function translateReason(
    value: unknown
): string {
    const key =
        String(
            value || ""
        )
            .trim()
            .toLowerCase();

    const reasonKeys: Record<string, string> = {
        "improves weak muscle group":
            "recommendations.reasons.improvesWeakMuscleGroup",
        "improves weak movement pattern":
            "recommendations.reasons.improvesWeakMovementPattern",
        "helps reverse regression":
            "recommendations.reasons.helpsReverseRegression",
        "helps break plateau":
            "recommendations.reasons.helpsBreakPlateau",
        "supports an undertrained muscle":
            "recommendations.reasons.supportsAnUndertrainedMuscle",
        "adds exercise variety":
            "recommendations.reasons.addsExerciseVariety",
        "targets your weak point":
            "recommendations.reasons.targetsYourWeakPoint",
        progression:
            "recommendations.reasons.progression",
        "low frequency":
            "recommendations.reasons.lowFrequency",
        "high frequency":
            "recommendations.reasons.highFrequency"
    };

    const translationKey =
        reasonKeys[key];

    if (!translationKey) {
        return capitalize(value);
    }

    const translated =
        t(translationKey);

    return translated !== translationKey
        ? translated
        : capitalize(value);
}

export function renderRecommendations(
    data: RecommendationsData | null | undefined
): void {
    const muscles =
        data?.muscles || {};

    const recommendations =
        safeArray(
            data?.recommended_exercises
        );

    renderWeakPoints(
        muscles
    );

    renderRecommendedExercises(
        recommendations
    );

    renderBalance(
        muscles
    );
}

function renderWeakPoints(
    muscles: MuscleData
): void {
    const box =
        document.getElementById(
            "tr-weak-points"
        );

    if (!box) {
        return;
    }

    const items =
        safeArray(
            muscles.weak
        )
            .filter(Boolean)
            .slice(0, 4);

    if (items.length === 0) {
        box.innerHTML = `
            <div class="tr-rec-empty">
                <strong>${t("recommendations.weakPointsEmpty")}</strong>
                <span>${t("recommendations.weakPointsDescription")}</span>
            </div>
        `;

        return;
    }

    box.innerHTML =
        items
            .map(
                muscle => `
                    <div class="tr-weak-item">
                        ${translateMuscle(muscle)}
                    </div>
                `
            )
            .join("");
}

function renderRecommendedExercises(
    list: RecommendationItem[]
): void {
    const box =
        document.getElementById(
            "tr-rec-grid"
        );

    if (!box) {
        return;
    }

    const items =
        list
            .filter(
                item =>
                    item &&
                    typeof item.exercise === "string" &&
                    item.exercise.trim().length > 0
            )
            .slice(0, 3);

    if (items.length === 0) {
        box.innerHTML = `
            <div class="tr-rec-empty">
                <strong>${t("recommendations.exercisesEmpty")}</strong>
                <span>${t("recommendations.exercisesDescription")}</span>
            </div>
        `;

        return;
    }

    box.innerHTML =
        items
            .map(item => {
                const reasons =
                    safeArray(
                        item.reasons
                    )
                        .filter(Boolean)
                        .slice(0, 2);

                return `
                    <div class="tr-rec-line-item">
                        <div class="tr-rec-line-item-top">
                            ${ICONS.exercise}
                            <span>${item.exercise || ""}</span>
                        </div>

                        ${
                            reasons.length > 0
                                ? reasons
                                      .map(
                                          reason => `
                                            <div class="tr-rec-item-tag">
                                                ${translateReason(reason)}
                                            </div>
                                        `
                                      )
                                      .join("")
                                : ""
                        }
                    </div>
                `;
            })
            .join("");
}

function renderBalance(
    muscles: MuscleData
): void {
    const balancedBox =
        document.getElementById(
            "tr-balance-balanced"
        );

    const overloadedBox =
        document.getElementById(
            "tr-balance-overloaded"
        );

    if (
        !balancedBox ||
        !overloadedBox
    ) {
        return;
    }

    const balanced =
        safeArray(
            muscles.balanced
        )
            .filter(Boolean)
            .slice(0, 3);

    const overloaded =
        safeArray(
            muscles.overloaded
        )
            .filter(Boolean)
            .slice(0, 3);

    if (
        balanced.length === 0 &&
        overloaded.length === 0
    ) {
        balancedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <strong>${t("recommendations.balanceEmpty")}</strong>
                <span>${t("recommendations.balanceDescription")}</span>
            </div>
        `;

        overloadedBox.innerHTML = "";

        return;
    }

    if (balanced.length === 0) {
        balancedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <span>${t("recommendations.noBalancedGroups")}</span>
            </div>
        `;
    } else {
        balancedBox.innerHTML =
            balanced
                .map(
                    muscle => `
                        <div class="tr-balance-item tr-balance-item-balanced">
                            ${ICONS.balanced}
                            <span>${translateMuscle(muscle)}</span>
                        </div>
                    `
                )
                .join("");
    }

    if (overloaded.length === 0) {
        overloadedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <span>${t("recommendations.noOverloadedGroups")}</span>
            </div>
        `;
    } else {
        overloadedBox.innerHTML =
            overloaded
                .map(
                    muscle => `
                        <div class="tr-balance-item tr-balance-item-overloaded">
                            ${ICONS.overloaded}
                            <span>${translateMuscle(muscle)}</span>
                        </div>
                    `
                )
                .join("");
    }
}