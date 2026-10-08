import { ICONS } from "../icons/index.js";

import {
    exercise_t,
    t
} from "../i18n/index.js";

type RecommendationItem = {
    exercise?: string;
    slug?: string;
    reasons?: string[];
    score?: number;
};

// "What to train today and why", decided by the training model on the
// backend. Every text is an i18n key; nothing is computed here.
type GuidanceItem = {
    muscle?: string;
    kind?: string;
    label?: string;
    reasons?: string[];
    action?: string;
    params?: Record<string, string | number>;
};

type Guidance = {
    verdict?: string;
    title?: string;
    message?: string;
    muscles?: GuidanceItem[];
    warnings?: GuidanceItem[];
};

export type RecommendationsData = {
    load?: unknown;
    muscles?: unknown;
    patterns?: unknown;
    progression?: unknown;
    recovery?: unknown;
    diversity?: unknown;
    frequency?: unknown;
    recommended_exercises?: RecommendationItem[];
    summary?: string;
    guidance?: Guidance;
    [key: string]: unknown;
};

const GUIDANCE_KEY =
    "recommendations.training.guidance.";

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

export function translateMuscle(
    value: unknown
): string {
    const key =
        String(
            value || ""
        )
            .trim()
            .toLowerCase();

    const translationKey =
        `muscles.${key.replace(
            /-([a-z])/g,
            (_, letter: string) =>
                letter.toUpperCase()
        )}`;

    const translated =
        t(translationKey);

    return translated !== translationKey
        ? translated
        : capitalize(value);
}

// The backend sends i18n keys only; an unknown key is dropped rather than
// shown raw.
function translateKey(
    value: unknown,
    params: Record<string, string | number> = {}
): string {
    const key =
        String(
            value || ""
        ).trim();

    if (!key) {
        return "";
    }

    const translated =
        t(key, params);

    return translated !== key
        ? translated
        : "";
}

function translateExercise(
    item: RecommendationItem
): string {
    if (
        typeof item.slug === "string" &&
        item.slug.trim()
    ) {
        const translated =
            exercise_t(
                item.slug
            );

        if (
            translated !==
            `${item.slug}.name`
        ) {
            return translated;
        }
    }

    return item.exercise || "";
}

export function renderRecommendations(
    data: RecommendationsData | null | undefined
): void {
    renderGuidance(
        data?.guidance
    );

    renderRecommendedExercises(
        safeArray(
            data?.recommended_exercises
        ),
        Boolean(
            data?.guidance?.verdict &&
            data.guidance.verdict !== "no_history"
        )
    );
}

function renderGuidanceItem(
    item: GuidanceItem
): string {
    const kind =
        String(
            item.kind || ""
        ).replace(/[^a-z_]/g, "");

    const reasons =
        safeArray(
            item.reasons
        )
            .map(reason => translateKey(reason))
            .filter(Boolean);

    const action =
        translateKey(
            item.action,
            item.params ?? {}
        );

    return `
        <div class="tr-guidance-item tr-guidance-item-${kind}">
            <div class="tr-guidance-item-top">
                <span class="tr-guidance-muscle">
                    ${translateMuscle(item.muscle)}
                </span>

                <span class="tr-guidance-badge">
                    ${translateKey(item.label)}
                </span>
            </div>

            ${reasons
                .map(
                    reason => `
                        <div class="tr-guidance-reason">
                            ${reason}
                        </div>
                    `
                )
                .join("")}

            ${
                action
                    ? `<div class="tr-guidance-action">${action}</div>`
                    : ""
            }
        </div>
    `;
}

function renderGuidance(
    guidance: Guidance | undefined
): void {
    const box =
        document.getElementById(
            "tr-guidance"
        );

    if (!box) {
        return;
    }

    const verdict =
        String(
            guidance?.verdict || "no_history"
        ).replace(/[^a-z_]/g, "");

    const title =
        translateKey(
            guidance?.title ||
            `${GUIDANCE_KEY}verdict.no_history.title`
        );

    const message =
        translateKey(
            guidance?.message ||
            `${GUIDANCE_KEY}verdict.no_history.message`
        );

    const muscles =
        safeArray(
            guidance?.muscles
        ).filter(item => item && item.muscle);

    const warnings =
        safeArray(
            guidance?.warnings
        ).filter(item => item && item.muscle);

    box.innerHTML = `
        <div class="tr-guidance-verdict tr-guidance-verdict-${verdict}">
            <strong>${title}</strong>
            <span>${message}</span>
        </div>

        ${
            muscles.length > 0
                ? `
                    <div class="tr-guidance-list">
                        ${muscles.map(renderGuidanceItem).join("")}
                    </div>
                `
                : ""
        }

        ${
            warnings.length > 0
                ? `
                    <div class="tr-guidance-subtitle">
                        ${t(`${GUIDANCE_KEY}holdBack`)}
                    </div>

                    <div class="tr-guidance-list">
                        ${warnings.map(renderGuidanceItem).join("")}
                    </div>
                `
                : ""
        }
    `;
}

function renderRecommendedExercises(
    list: RecommendationItem[],
    hasHistory: boolean
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
                    (
                        typeof item.exercise === "string" ||
                        typeof item.slug === "string"
                    ) &&
                    (
                        item.exercise?.trim().length ||
                        item.slug?.trim().length
                    )
            )
            .slice(0, 3);

    if (items.length === 0) {
        // With training history an empty list means nothing needs extra
        // work, not that there is too little data.
        box.innerHTML = hasHistory
            ? `
                <div class="tr-rec-empty">
                    <span>${t(`${GUIDANCE_KEY}noExercises`)}</span>
                </div>
            `
            : `
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
                        .map(reason => translateKey(reason))
                        .filter(Boolean)
                        .slice(0, 2);

                return `
                    <div class="tr-rec-line-item">
                        <div class="tr-rec-line-item-top">
                            ${ICONS.exercise}
                            <span>${translateExercise(item)}</span>
                        </div>

                        ${reasons
                            .map(
                                reason => `
                                    <div class="tr-rec-item-tag">
                                        ${reason}
                                    </div>
                                `
                            )
                            .join("")}
                    </div>
                `;
            })
            .join("");
}
