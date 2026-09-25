import {
    translate
} from "../i18n/loader.js";
import { ICONS } from "../icons/index.js";
import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createLoading,
    createError,
    createEmpty
} from "./dom.js";

import type {
    RecoverySnapshot
} from "./api.js";

interface RenderOptions {
    loading?: boolean;
    error?: string | null;
}

function normalize(
    value: unknown
): number {
    const num =
        Number(value);

    if (
        Number.isNaN(num)
    ) {
        return 0;
    }

    if (
        num <= 5
    ) {
        return num * 20;
    }

    return Math.max(
        0,
        Math.min(
            num,
            100
        )
    );
}

function getLevel(
    value: unknown
): "low" | "medium" | "high" {
    const score =
        normalize(value);

    if (
        score < 40
    ) {
        return "low";
    }

    if (
        score < 70
    ) {
        return "medium";
    }

    return "high";
}

function getStatus(
    value: unknown
): string {
    const score =
        normalize(value);

    if (
        score < 40
    ) {
        return translate(
            "recovery",
            "score.status.attention"
        );
    }

    if (
        score < 70
    ) {
        return translate(
            "recovery",
            "score.status.medium"
        );
    }

    if (
        score < 85
    ) {
        return translate(
            "recovery",
            "score.status.good"
        );
    }

    return translate(
        "recovery",
        "score.status.excellent"
    );
}

function createBar(
    score: unknown
): HTMLDivElement {
    const bar =
        document.createElement(
            "div"
        );

    bar.className =
        "score-bar";

    const normalized =
        normalize(score);

    const filled =
        Math.round(
            normalized / 20
        );

    const level =
        getLevel(score);

    for (
        let i = 0;
        i < 5;
        i += 1
    ) {
        const segment =
            document.createElement(
                "div"
            );

        segment.className =
            "score-segment";

        if (
            i < filled
        ) {
            segment.classList.add(
                "filled",
                level
            );
        }

        bar.appendChild(
            segment
        );
    }

    return bar;
}

function createItem(
    iconSvg: string,
    label: string,
    score: unknown
): HTMLDivElement {
    const item =
        document.createElement(
            "div"
        );

    item.className =
        "score-item";

    const top =
        document.createElement(
            "div"
        );

    top.className =
        "score-top";

    const left =
        document.createElement(
            "div"
        );

    left.className =
        "score-left";

    const icon =
        document.createElement(
            "span"
        );

    icon.className =
        "score-icon";

    icon.innerHTML =
        iconSvg;

    const text =
        document.createElement(
            "span"
        );

    text.className =
        "score-label";

    text.textContent =
        label;

    left.appendChild(
        icon
    );

    left.appendChild(
        text
    );

    const value =
        document.createElement(
            "span"
        );

    value.className =
        "score-value";

    value.textContent =
        `${normalize(score)}%`;

    top.appendChild(
        left
    );

    top.appendChild(
        value
    );

    const bar =
        createBar(
            score
        );

    const status =
        document.createElement(
            "div"
        );

    status.className =
        "score-status";

    status.textContent =
        getStatus(
            score
        );

    item.appendChild(
        top
    );

    item.appendChild(
        bar
    );

    item.appendChild(
        status
    );

    return item;
}

export function renderScoreWidget(
    snapshot: RecoverySnapshot | null,
    options: RenderOptions = {}
): void {
    const el =
        document.getElementById(
            "score-widget"
        );

    if (!el) {
        return;
    }

    clearElement(
        el
    );

    if (
        options.loading
    ) {
        el.appendChild(
            createLoading(
                RECOVERY_MESSAGES.loading
            )
        );

        return;
    }

    if (
        options.error
    ) {
        el.appendChild(
            createError(
                RECOVERY_MESSAGES.error
            )
        );

        return;
    }

    if (!snapshot) {
        el.appendChild(
            createEmpty(
                RECOVERY_MESSAGES.score.empty
            )
        );

        return;
    }

    const card =
        createCard(
            "score-card"
        );

    card.appendChild(
        createItem(
            ICONS.moon || "",
            translate(
                "recovery",
                "score.labels.sleep"
            ),
            snapshot.sleep_score
        )
    );

    card.appendChild(
        createItem(
            ICONS.exercise || "",
            translate(
                "recovery",
                "score.labels.training"
            ),
            snapshot.training_score
        )
    );

    card.appendChild(
        createItem(
            ICONS.zap || "",
            translate(
                "recovery",
                "score.labels.energy"
            ),
            snapshot.energy_score
        )
    );

    card.appendChild(
        createItem(
            ICONS.calendar_cog || "",
            translate(
                "recovery",
                "score.labels.habits"
            ),
            snapshot.habits_score
        )
    );

    el.appendChild(
        card
    );
}