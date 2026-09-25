import {
    ICONS
} from "../../../icons/index.js";

import {
    recovery_t
} from "../../../i18n/index.js";

import {
    createMiniCard
} from "./day_card.js";

import type {
    RecoveryHabit,
    RecoveryRecommendation
} from "../../api.js";

type IconKey =
    keyof typeof ICONS;

const ICON_ALIASES: Record<
    string,
    IconKey
> = {
    recovery: "rest",
    activity: "mobility",
    sleep: "bed",
    nutrition: "meal",
    water: "droplet",
    hydration: "droplet",
    electrolyte: "electrolytes",
    electrolytes: "electrolytes",
    stretch: "stretch",
    mobility: "mobility",
    foam_roll: "foam_roll",
    breathing: "breathing",
    meditation: "meditation",
    journal: "journal",
    rest: "rest",
    massage: "massage",
    deload: "deload"
};

const RECOMMENDATION_ICONS: Record<
    string,
    IconKey
> = {
    recovery: "rest",
    habit: "rest",
    training: "mobility",
    sleep: "bed",
    nutrition: "meal",
    activity: "mobility"
};

const MUSCLE_KEYS: Record<
    string,
    string
> = {
    chest: "chest",
    back: "back",
    shoulders: "shoulders",
    biceps: "biceps",
    triceps: "triceps",
    forearms: "forearms",
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
    key: string | null | undefined
): string {
    if (!key) {
        return "";
    }

    const resolvedKey =
        ICON_ALIASES[key] ?? key;

    if (
        resolvedKey in ICONS
    ) {
        return ICONS[
            resolvedKey as IconKey
        ];
    }

    return "";
}

function getRecommendationIcon(
    recommendation: RecoveryRecommendation
): string {
    if (
        recommendation.icon
    ) {
        const icon =
            getIcon(
                recommendation.icon
            );

        if (icon) {
            return icon;
        }
    }

    if (
        recommendation.type
    ) {
        const iconKey =
            RECOMMENDATION_ICONS[
                recommendation.type
            ];

        if (iconKey) {
            return ICONS[
                iconKey
            ];
        }
    }

    return ICONS.rest;
}

function formatScore(
    value: number | null | undefined
): string {
    if (
        value == null ||
        !Number.isFinite(
            Number(value)
        )
    ) {
        return "—";
    }

    return String(
        Math.round(
            Number(value)
        )
    );
}

function getStatus(
    value: number | null | undefined
): string {
    if (
        value == null
    ) {
        return recovery_t(
            "status.no_data"
        );
    }

    if (
        value >= 80
    ) {
        return recovery_t(
            "status.good"
        );
    }

    if (
        value >= 60
    ) {
        return recovery_t(
            "status.normal"
        );
    }

    if (
        value >= 40
    ) {
        return recovery_t(
            "status.attention"
        );
    }

    return recovery_t(
        "status.low"
    );
}

function getBarFill(
    value: number | null | undefined
): number {
    if (
        value == null ||
        !Number.isFinite(
            Number(value)
        )
    ) {
        return 0;
    }

    return Math.max(
        0,
        Math.min(
            100,
            Number(value)
        )
    );
}

function getHabitName(
    habit: RecoveryHabit
): string {
    if (
        habit.slug
    ) {
        const key =
            `habits.${habit.slug}.name`;

        const translated =
            recovery_t(
                key
            );

        if (
            translated !== key
        ) {
            return translated;
        }
    }

    return (
        habit.name ||
        recovery_t(
            "habit.fallback"
        )
    );
}

function getHabitCategory(
    category?: string | null
): string {
    if (!category) {
        return "";
    }

    const key =
        `categories.${category}`;

    const translated =
        recovery_t(
            key
        );

    return translated === key
        ? category
        : translated;
}

function getHabitStatus(
    completed: boolean
): string {
    return completed
        ? recovery_t(
            "day_details.completed"
        )
        : recovery_t(
            "day_details.not_completed"
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
            .replace(
                /-/g,
                "_"
            );

    const key =
        MUSCLE_KEYS[
            normalized
        ];

    if (!key) {
        return muscle;
    }

    const translationKey =
        `muscles.${key}`;

    const translated =
        recovery_t(
            translationKey
        );

    return translated === translationKey
        ? muscle
        : translated;
}

function getRecommendationKey(
    recommendation: RecoveryRecommendation
): string | null {
    const id =
        recommendation.id;

    if (!id) {
        return null;
    }

    if (
        id.startsWith("rest_")
    ) {
        return "rest_muscle";
    }

    if (
        id.startsWith("train_")
    ) {
        return "train_muscle";
    }

    return id;
}

function getRecommendationParams(
    recommendation: RecoveryRecommendation
): Record<
    string,
    string | number
> {
    return {
        muscle:
            getMuscleName(
                recommendation.muscle
            )
    };
}

function getRecommendationText(
    recommendation: RecoveryRecommendation
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

    const translationKey =
        `recommendations.items.${key}.text`;

    const translated =
        recovery_t(
            translationKey,
            getRecommendationParams(
                recommendation
            )
        );

    if (
        translated !== translationKey
    ) {
        return translated;
    }

    return (
        recommendation.text ||
        recommendation.description ||
        recommendation.message ||
        ""
    );
}

function getRecommendationTitle(
    recommendation: RecoveryRecommendation
): string {
    const key =
        getRecommendationKey(
            recommendation
        );

    if (!key) {
        return "";
    }

    const translationKey =
        `recommendations.items.${key}.title`;

    const translated =
        recovery_t(
            translationKey,
            getRecommendationParams(
                recommendation
            )
        );

    return translated === translationKey
        ? ""
        : translated;
}

export function createSummaryCard(
    name: string,
    value: string | number,
    status: string,
    barFill = 0
): HTMLDivElement {
    return createMiniCard(
        name,
        value,
        status,
        barFill
    );
}

export function createDailySummary(
    data: {
        recovery?: {
            score?: number | null;
        };
        sleep?: {
            quality_score?: number | null;
        };
        training?: {
            load?: number | null;
        };
        habits?: {
            score?: number | null;
        };
    }
): HTMLDivElement {
    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "rc-daily-summary";

    const recovery =
        data.recovery?.score ??
        null;

    const sleep =
        data.sleep?.quality_score ??
        null;

    const training =
        data.training?.load ??
        null;

    const habits =
        data.habits?.score ??
        null;

    wrapper.appendChild(
        createSummaryCard(
            recovery_t(
                "summary.recovery"
            ),
            formatScore(
                recovery
            ),
            getStatus(
                recovery
            ),
            getBarFill(
                recovery
            )
        )
    );

    wrapper.appendChild(
        createSummaryCard(
            recovery_t(
                "summary.sleep"
            ),
            formatScore(
                sleep
            ),
            getStatus(
                sleep
            ),
            getBarFill(
                sleep
            )
        )
    );

    wrapper.appendChild(
        createSummaryCard(
            recovery_t(
                "summary.load"
            ),
            training == null
                ? "—"
                : Math.round(
                    training
                ),
            training == null
                ? recovery_t(
                    "status.no_data"
                )
                : recovery_t(
                    "summary.training"
                ),
            training == null
                ? 0
                : Math.min(
                    100,
                    Math.max(
                        0,
                        training
                    )
                )
        )
    );

    wrapper.appendChild(
        createSummaryCard(
            recovery_t(
                "summary.habits"
            ),
            formatScore(
                habits
            ),
            getStatus(
                habits
            ),
            getBarFill(
                habits
            )
        )
    );

    return wrapper;
}

export function createHabitsGrid(
    habits: RecoveryHabit[]
): HTMLDivElement {
    const grid =
        document.createElement(
            "div"
        );

    grid.className =
        "rc-habits-grid";

    habits.forEach(
        habit => {
            grid.appendChild(
                createHabitRow(
                    habit
                )
            );
        }
    );

    if (
        habits.length === 0
    ) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "rc-empty-state";

        empty.textContent =
            recovery_t(
                "day_details.no_habits"
            );

        grid.appendChild(
            empty
        );
    }

    return grid;
}

export function createHabitRow(
    habit: RecoveryHabit
): HTMLDivElement {
    const row =
        document.createElement(
            "div"
        );

    row.className =
        "rc-habit-row";

    if (
        habit.completed
    ) {
        row.classList.add(
            "completed"
        );
    }

    const icon =
        document.createElement(
            "div"
        );

    icon.className =
        "rc-habit-icon";

    icon.setAttribute(
        "aria-hidden",
        "true"
    );

    const iconMarkup =
        getIcon(
            habit.icon
        );

    if (
        iconMarkup
    ) {
        icon.innerHTML =
            iconMarkup;
    }

    const content =
        document.createElement(
            "div"
        );

    content.className =
        "rc-habit-meta";

    const name =
        document.createElement(
            "div"
        );

    name.className =
        "rc-habit-name";

    name.textContent =
        getHabitName(
            habit
        );

    content.appendChild(
        name
    );

    if (
        habit.category
    ) {
        const category =
            document.createElement(
                "div"
            );

        category.className =
            "rc-habit-category";

        category.textContent =
            getHabitCategory(
                habit.category
            );

        content.appendChild(
            category
        );
    }

    const status =
        document.createElement(
            "div"
        );

    status.className =
        "rc-habit-status";

    status.textContent =
        getHabitStatus(
            Boolean(
                habit.completed
            )
        );

    row.appendChild(
        icon
    );

    row.appendChild(
        content
    );

    row.appendChild(
        status
    );

    return row;
}

export function createRecommendationRow(
    recommendation: RecoveryRecommendation
): HTMLDivElement {
    const row =
        document.createElement(
            "div"
        );

    row.className =
        "rc-recommendation";

    if (
        recommendation.priority
    ) {
        row.dataset.priority =
            String(
                recommendation.priority
            );
    }

    const icon =
        document.createElement(
            "div"
        );

    icon.className =
        "rc-rec-icon";

    icon.setAttribute(
        "aria-hidden",
        "true"
    );

    icon.innerHTML =
        getRecommendationIcon(
            recommendation
        );

    const body =
        document.createElement(
            "div"
        );

    body.className =
        "rc-rec-body";

    const title =
        getRecommendationTitle(
            recommendation
        );

    const text =
        getRecommendationText(
            recommendation
        );

    if (
        title
    ) {
        const titleElement =
            document.createElement(
                "div"
            );

        titleElement.className =
            "rc-rec-title";

        titleElement.textContent =
            title;

        body.appendChild(
            titleElement
        );
    }

    if (
        text
    ) {
        const textElement =
            document.createElement(
                "div"
            );

        textElement.className =
            "rc-rec-text";

        textElement.textContent =
            text;

        body.appendChild(
            textElement
        );
    }

    if (
        !title &&
        !text
    ) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "rc-rec-text";

        empty.textContent =
            recovery_t(
                "day_details.recommendation"
            );

        body.appendChild(
            empty
        );
    }

    row.appendChild(
        icon
    );

    row.appendChild(
        body
    );

    return row;
}
