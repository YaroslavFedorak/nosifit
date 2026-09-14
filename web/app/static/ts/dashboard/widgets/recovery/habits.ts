import { ICONS } from "../../../icons/index.js";
import { RecoveryAPI } from "../../modals/recovery/api.js";
import { refreshRecoveryWidget } from "./index.js";

import type {
    RecoveryHabit,
    RecoverySnapshot
} from "./state.js";

const CATEGORY_LABELS:
    Record<string, string> = {
    sleep: "Сон",
    hydration: "Вода",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};

function getIcon(
    iconKey?: string
): string {
    if (
        iconKey &&
        iconKey in ICONS
    ) {
        return ICONS[
            iconKey as keyof typeof ICONS
        ];
    }

    return ICONS.rest;
}

function getCategoryLabel(
    category?: string
): string {
    if (!category) {
        return "";
    }

    return (
        CATEGORY_LABELS[category] ||
        category
    );
}

function buildReason(
    habit: RecoveryHabit
): string {
    switch (habit.category) {
        case "sleep":
            return "Рекомендовано через якість сну";

        case "hydration":
            return "Рекомендовано через рівень гідратації";

        case "nutrition":
            return "Рекомендовано для підтримки харчування";

        case "activity":
            return "Рекомендовано після навантаження";

        case "recovery":
            return "Рекомендовано для покращення відновлення";

        case "stress":
            return "Рекомендовано через рівень стресу";

        case "massage":
            return "Рекомендовано для розслаблення м'язів";

        default:
            return "Рекомендовано для балансу відновлення";
    }
}

function normalizeHabits(
    snapshot:
        RecoverySnapshot
        | null
): RecoveryHabit[] {
    if (!snapshot) {
        return [];
    }

    const rawHabits =
        snapshot.habits;

    if (!Array.isArray(rawHabits)) {
        return [];
    }

    return rawHabits
        .filter(
            value =>
                value !== null &&
                typeof value === "object"
        )
        .map(value => {
            const raw =
                value as Record<
                    string,
                    unknown
                >;

            const userHabit =
                raw.user_habit &&
                typeof raw.user_habit ===
                    "object"
                    ? raw.user_habit as Record<
                        string,
                        unknown
                    >
                    : null;

            const habit =
                raw.habit &&
                typeof raw.habit ===
                    "object"
                    ? raw.habit as Record<
                        string,
                        unknown
                    >
                    : null;

            const userHabitId =
                raw.user_habit_id ??
                raw.userHabitId ??
                userHabit?.id;

            const id =
                raw.id ??
                raw.habit_id ??
                raw.habitId ??
                habit?.id;

            const name =
                raw.name ??
                habit?.name ??
                "";

            const category =
                raw.category ??
                habit?.category;

            const icon =
                raw.icon ??
                habit?.icon;

            const points =
                raw.points ??
                habit?.points;

            const completed =
                raw.completed ??
                raw.completed_today ??
                raw.done_today ??
                false;

            return {
                ...raw,
                id:
                    id != null
                        ? Number(id)
                        : undefined,
                user_habit_id:
                    userHabitId != null
                        ? Number(
                            userHabitId
                        )
                        : undefined,
                name:
                    String(name),
                category:
                    category != null
                        ? String(
                            category
                        )
                        : undefined,
                icon:
                    icon != null
                        ? String(icon)
                        : undefined,
                points:
                    points != null
                        ? Number(points)
                        : undefined,
                completed:
                    Boolean(
                        completed
                    )
            } as RecoveryHabit;
        })
        .filter(
            habit =>
                Number(
                    habit.user_habit_id
                ) > 0
        );
}

function createHabitItem(
    habit: RecoveryHabit
): HTMLElement {
    const item =
        document.createElement(
            "div"
        );

    item.className =
        `habit-item ${
            habit.completed
                ? "habit-completed"
                : ""
        } habit-user`;

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
        getIcon(
            habit.icon
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
        habit.name || "";

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
        getCategoryLabel(
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
            `Recovery +${habit.points}`;
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
        String(
            habit.user_habit_id ?? ""
        );

    if (habit.completed) {
        check.classList.add(
            "habit-check-completed"
        );
    }

    check.title =
        habit.completed
            ? "Відмінити"
            : "Позначити як виконано";

    check.addEventListener(
        "click",
        async () => {
            const userHabitId =
                check.dataset
                    .userHabitId;

            if (!userHabitId) {
                return;
            }

            check.disabled =
                true;

            const wasCompleted =
                check.classList.contains(
                    "habit-check-completed"
                );

            check.classList.toggle(
                "habit-check-completed"
            );

            item.classList.toggle(
                "habit-completed"
            );

            try {
                await RecoveryAPI.logHabit(
                    userHabitId
                );

                await refreshRecoveryWidget();
            } catch (error) {
                console.error(
                    "Failed to log recovery habit",
                    error
                );

                if (
                    wasCompleted
                ) {
                    check.classList.remove(
                        "habit-check-completed"
                    );

                    item.classList.remove(
                        "habit-completed"
                    );
                } else {
                    check.classList.add(
                        "habit-check-completed"
                    );

                    item.classList.add(
                        "habit-completed"
                    );
                }
            } finally {
                check.disabled =
                    false;
            }
        }
    );

    const removeButton =
        document.createElement(
            "button"
        );

    removeButton.type =
        "button";

    removeButton.className =
        "habit-btn-remove";

    removeButton.innerHTML =
        ICONS.delete;

    removeButton.dataset.userHabitId =
        String(
            habit.user_habit_id ?? ""
        );

    let confirmationPending =
        false;

    let confirmationTimeout:
        ReturnType<
            typeof setTimeout
        > | null = null;

    removeButton.addEventListener(
        "click",
        async () => {
            const userHabitId =
                removeButton.dataset
                    .userHabitId;

            if (!userHabitId) {
                return;
            }

            if (
                !confirmationPending
            ) {
                confirmationPending =
                    true;

                removeButton.classList.add(
                    "habit-remove-pending"
                );

                confirmationTimeout =
                    setTimeout(
                        () => {
                            confirmationPending =
                                false;

                            removeButton.classList.remove(
                                "habit-remove-pending"
                            );

                            confirmationTimeout =
                                null;
                        },
                        2000
                    );

                return;
            }

            if (
                confirmationTimeout !==
                null
            ) {
                clearTimeout(
                    confirmationTimeout
                );

                confirmationTimeout =
                    null;
            }

            removeButton.disabled =
                true;

            try {
                await RecoveryAPI.removeHabit(
                    userHabitId
                );

                await refreshRecoveryWidget();
            } catch (error) {
                console.error(
                    "Failed to remove recovery habit",
                    error
                );
            } finally {
                confirmationPending =
                    false;

                removeButton.classList.remove(
                    "habit-remove-pending"
                );

                removeButton.disabled =
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
        removeButton
    );

    item.appendChild(
        main
    );

    item.appendChild(
        actions
    );

    return item;
}

function createHabitsList(
    habits: RecoveryHabit[]
): HTMLElement {
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

function createContainer(
    habits: RecoveryHabit[]
): HTMLElement {
    const container =
        document.createElement(
            "div"
        );

    container.className =
        "habits-widget-container";

    const header =
        document.createElement(
            "div"
        );

    header.className =
        "habits-widget-container-header";

    const title =
        document.createElement(
            "div"
        );

    title.className =
        "habits-widget-container-title";

    title.textContent =
        "Ваші звички";

    const count =
        document.createElement(
            "div"
        );

    count.className =
        "habits-widget-container-count";

    count.textContent =
        String(
            habits.length
        );

    header.appendChild(
        title
    );

    header.appendChild(
        count
    );

    container.appendChild(
        header
    );

    container.appendChild(
        createHabitsList(
            habits
        )
    );

    return container;
}

export function renderHabitsWidget(
    snapshot:
        RecoverySnapshot
        | null
): void {
    const element =
        document.getElementById(
            "dashboard-habits-list"
        );

    if (!element) {
        return;
    }

    element.innerHTML =
        "";

    const habits =
        normalizeHabits(
            snapshot
        );

    if (
        habits.length === 0
    ) {
        element.textContent =
            "Звички ще не додані";

        return;
    }

    const preview =
        habits.slice(
            0,
            8
        );

    element.appendChild(
        createContainer(
            preview
        )
    );
}