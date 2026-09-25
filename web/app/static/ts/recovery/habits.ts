import { RECOVERY_MESSAGES } from "./messages.js";

import {
    clearElement,
    createEmpty
} from "./dom.js";

import { RecoveryAPI } from "./api.js";

import {
    refreshRecoveryDashboard
} from "./dashboard.js";

import {
    showRecoveryToast
} from "./toast.js";

import {
    ICONS
} from "../icons/index.js";

import {
    recovery_t
} from "../i18n/index.js";

import type {
    RecoveryHabit
} from "./api.js";

interface RenderOptions {
    loading?: boolean;
    error?: string | null;
}

const ICON_MAP =
    ICONS as Record<string, string>;

const CATEGORY_ICONS: Record<string, string> = {
    sleep: "bed",
    hydration: "droplet",
    nutrition: "meal",
    activity: "walk",
    recovery: "rest",
    stress: "breathing",
    massage: "massage"
};

function getUserHabitId(
    habit: RecoveryHabit
): string {
    const value =
        habit.user_habit_id ??
        "";

    return String(
        value
    );
}

function getHabitSlug(
    habit: RecoveryHabit
): string {
    return (
        habit.slug ||
        ""
    );
}

function label(
    category?: string | null
): string {
    if (!category) {
        return "";
    }

    return recovery_t(
        `categories.${category}`
    );
}

function getHabitName(
    habit: RecoveryHabit
): string {
    const slug =
        getHabitSlug(
            habit
        );

    if (slug) {
        return recovery_t(
            `habits.${slug}.name`
        );
    }

    return habit.name || "";
}

function getHabitIcon(
    habit: RecoveryHabit
): string {
    const habitIcon =
        habit.icon || "";

    if (
        habitIcon &&
        ICON_MAP[habitIcon]
    ) {
        return ICON_MAP[
            habitIcon
        ];
    }

    const categoryIcon =
        CATEGORY_ICONS[
            habit.category || ""
        ];

    if (
        categoryIcon &&
        ICON_MAP[categoryIcon]
    ) {
        return ICON_MAP[
            categoryIcon
        ];
    }

    return ICON_MAP.rest || "";
}

function buildReason(
    habit: RecoveryHabit
): string {
    if (!habit.category) {
        return recovery_t(
            "reasons.default"
        );
    }

    return recovery_t(
        `reasons.${habit.category}`
    );
}

function createHabitItem(
    habit: RecoveryHabit
): HTMLDivElement {
    const item =
        document.createElement(
            "div"
        );

    const userHabitId =
        getUserHabitId(
            habit
        );

    item.className = [
        "habit-item",
        habit.completed
            ? "habit-completed"
            : "",
        "habit-user"
    ]
        .filter(Boolean)
        .join(" ");

    if (habit.category) {
        item.classList.add(
            `habit-cat-${habit.category}`
        );
    }

    const main =
        document.createElement(
            "div"
        );

    main.className =
        "habit-main";

    const iconBox =
        document.createElement(
            "div"
        );

    iconBox.className =
        "habit-icon";

    iconBox.innerHTML =
        getHabitIcon(
            habit
        );

    const textBox =
        document.createElement(
            "div"
        );

    textBox.className =
        "habit-text";

    const title =
        document.createElement(
            "div"
        );

    title.className =
        "habit-title";

    title.textContent =
        getHabitName(
            habit
        );

    const metaRow =
        document.createElement(
            "div"
        );

    metaRow.className =
        "habit-meta-row";

    const category =
        document.createElement(
            "div"
        );

    category.className =
        "habit-category-badge";

    category.textContent =
        label(
            habit.category
        );

    const reason =
        document.createElement(
            "div"
        );

    reason.className =
        "habit-reason";

    reason.textContent =
        buildReason(
            habit
        );

    metaRow.appendChild(
        category
    );

    textBox.appendChild(
        title
    );

    textBox.appendChild(
        metaRow
    );

    textBox.appendChild(
        reason
    );

    main.appendChild(
        iconBox
    );

    main.appendChild(
        textBox
    );

    const actions =
        document.createElement(
            "div"
        );

    actions.className =
        "habit-actions";

    const impact =
        document.createElement(
            "div"
        );

    impact.className =
        "habit-recovery-impact";

    if (
        habit.points != null
    ) {
        impact.textContent =
            `${recovery_t("points.label")} +${habit.points}`;
    }

    const check =
        document.createElement(
            "button"
        );

    check.type =
        "button";

    check.className =
        "habit-check";

    check.dataset.userHabitId =
        userHabitId;

    if (
        habit.completed
    ) {
        check.classList.add(
            "habit-check-completed"
        );
    }

    check.title =
        habit.completed
            ? recovery_t(
                "actions.cancel"
            )
            : recovery_t(
                "actions.complete"
            );

    check.addEventListener(
        "click",
        async () => {
            if (!userHabitId) {
                showRecoveryToast(
                    recovery_t(
                        "errors.unknown_habit"
                    )
                );

                return;
            }

            const wasCompleted =
                check.classList.contains(
                    "habit-check-completed"
                );

            check.disabled =
                true;

            check.classList.toggle(
                "habit-check-completed",
                !wasCompleted
            );

            item.classList.toggle(
                "habit-completed",
                !wasCompleted
            );

            item.classList.add(
                "habit-animate"
            );

            window.setTimeout(
                () => {
                    item.classList.remove(
                        "habit-animate"
                    );
                },
                160
            );

            try {
                if (
                    wasCompleted
                ) {
                    await RecoveryAPI.unlogHabit(
                        userHabitId
                    );

                    showRecoveryToast(
                        recovery_t(
                            "toast.uncompleted"
                        )
                    );
                } else {
                    await RecoveryAPI.logHabit(
                        userHabitId
                    );

                    showRecoveryToast(
                        recovery_t(
                            "toast.completed"
                        )
                    );
                }

                await refreshRecoveryDashboard();
            } catch {
                check.classList.toggle(
                    "habit-check-completed",
                    wasCompleted
                );

                item.classList.toggle(
                    "habit-completed",
                    wasCompleted
                );

                showRecoveryToast(
                    recovery_t(
                        "errors.save"
                    )
                );
            } finally {
                check.disabled =
                    false;
            }
        }
    );

    const removeBtn =
        document.createElement(
            "button"
        );

    removeBtn.type =
        "button";

    removeBtn.className =
        "habit-btn-remove";

    removeBtn.innerHTML =
        ICON_MAP.delete || "";

    removeBtn.dataset.userHabitId =
        userHabitId;

    let confirm =
        false;

    let timeoutId:
        number | null = null;

    removeBtn.addEventListener(
        "click",
        async () => {
            if (!userHabitId) {
                showRecoveryToast(
                    recovery_t(
                        "errors.unknown_habit"
                    )
                );

                return;
            }

            if (!confirm) {
                confirm =
                    true;

                removeBtn.classList.add(
                    "habit-remove-pending"
                );

                timeoutId =
                    window.setTimeout(
                        () => {
                            confirm =
                                false;

                            removeBtn.classList.remove(
                                "habit-remove-pending"
                            );

                            timeoutId =
                                null;
                        },
                        2000
                    );

                return;
            }

            if (
                timeoutId !== null
            ) {
                window.clearTimeout(
                    timeoutId
                );

                timeoutId =
                    null;
            }

            removeBtn.disabled =
                true;

            try {
                await RecoveryAPI.deleteHabit(
                    userHabitId
                );

                showRecoveryToast(
                    recovery_t(
                        "toast.deleted"
                    )
                );

                await refreshRecoveryDashboard();
            } catch {
                showRecoveryToast(
                    recovery_t(
                        "errors.delete"
                    )
                );
            } finally {
                confirm =
                    false;

                removeBtn.classList.remove(
                    "habit-remove-pending"
                );

                removeBtn.disabled =
                    false;
            }
        }
    );

    actions.appendChild(
        impact
    );

    actions.appendChild(
        check
    );

    actions.appendChild(
        removeBtn
    );

    item.appendChild(
        main
    );

    item.appendChild(
        actions
    );

    return item;
}

function renderHabitsGrid(
    habits: RecoveryHabit[]
): HTMLDivElement {
    const grid =
        document.createElement(
            "div"
        );

    grid.className =
        "habits-grid two-col";

    const left =
        document.createElement(
            "div"
        );

    left.className =
        "habits-col";

    const right =
        document.createElement(
            "div"
        );

    right.className =
        "habits-col";

    habits.forEach(
        (
            habit,
            index
        ) => {
            const column =
                index % 2 === 0
                    ? left
                    : right;

            column.appendChild(
                createHabitItem(
                    habit
                )
            );
        }
    );

    grid.appendChild(
        left
    );

    grid.appendChild(
        right
    );

    return grid;
}

export function renderHabitsWidget(
    habits: RecoveryHabit[] | null,
    options: RenderOptions = {}
): void {
    const el =
        document.getElementById(
            "habits-widget"
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
        el.textContent =
            RECOVERY_MESSAGES.loading;

        return;
    }

    if (
        options.error
    ) {
        el.textContent =
            RECOVERY_MESSAGES.error;

        return;
    }

    if (
        !Array.isArray(
            habits
        ) ||
        habits.length === 0
    ) {
        el.appendChild(
            createEmpty(
                RECOVERY_MESSAGES.habits.empty
            )
        );

        return;
    }

    const userAdded =
        habits.filter(
            habit =>
                habit &&
                habit.user_habit_id != null
        );

    if (
        userAdded.length === 0
    ) {
        el.appendChild(
            createEmpty(
                RECOVERY_MESSAGES.habits.empty
            )
        );

        return;
    }

    const previewCount =
        8;

    const preview =
        userAdded.slice(
            0,
            previewCount
        );

    el.appendChild(
        renderHabitsGrid(
            preview
        )
    );

    if (
        userAdded.length >
        previewCount
    ) {
        const footer =
            document.createElement(
                "div"
            );

        footer.className =
            "habits-widget-footer";

        const moreBtn =
            document.createElement(
                "button"
            );

        moreBtn.type =
            "button";

        moreBtn.className =
            "rc-btn rc-btn-sm";

        moreBtn.textContent =
            `${recovery_t("actions.show_all")} (${userAdded.length})`;

        moreBtn.addEventListener(
            "click",
            () => {
                clearElement(
                    el
                );

                el.appendChild(
                    renderHabitsGrid(
                        userAdded
                    )
                );

                const backFooter =
                    document.createElement(
                        "div"
                    );

                backFooter.className =
                    "habits-widget-footer";

                const backBtn =
                    document.createElement(
                        "button"
                    );

                backBtn.type =
                    "button";

                backBtn.className =
                    "rc-btn rc-btn-sm";

                backBtn.textContent =
                    recovery_t(
                        "actions.show_less"
                    );

                backBtn.addEventListener(
                    "click",
                    () =>
                        renderHabitsWidget(
                            habits
                        )
                );

                backFooter.appendChild(
                    backBtn
                );

                el.appendChild(
                    backFooter
                );
            }
        );

        footer.appendChild(
            moreBtn
        );

        el.appendChild(
            footer
        );
    }
}