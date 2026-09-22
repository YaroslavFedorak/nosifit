import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";
import { ICONS } from "../../icons/index.js";

import type {
    RecoveryHabit
} from "../api.js";

interface UserHabit {
    id?: number | string;
    habit_id?: number | string;
    user_habit_id?: number | string;
}

type SortMode =
    | "points"
    | "category"
    | "name";

interface HabitModalElements {
    backdrop: HTMLElement;
    list: HTMLElement;
    openButton: HTMLElement;
    backButton: HTMLButtonElement;
    saveButton: HTMLButtonElement;
    sortButtons: NodeListOf<HTMLButtonElement>;
}

const CATEGORY_LABELS: Record<string, string> = {
    sleep: "Сон",
    hydration: "Вода",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};

const CATEGORY_COLORS: Record<string, string> = {
    sleep: "#8b95b8",
    hydration: "#5b9db0",
    nutrition: "#b9a06d",
    activity: "#6fae87",
    recovery: "#9a7bb5",
    stress: "#b67c6b",
    massage: "#b58a9f"
};

const CATEGORY_BACKGROUNDS: Record<string, string> = {
    sleep: "rgba(139, 149, 184, 0.10)",
    hydration: "rgba(91, 157, 176, 0.10)",
    nutrition: "rgba(185, 160, 109, 0.10)",
    activity: "rgba(111, 174, 135, 0.10)",
    recovery: "rgba(154, 123, 181, 0.10)",
    stress: "rgba(182, 124, 107, 0.10)",
    massage: "rgba(181, 138, 159, 0.10)"
};

const CATEGORY_ICONS: Record<string, string> = {
    sleep: "bed",
    hydration: "droplet",
    nutrition: "meal",
    activity: "walk",
    recovery: "rest",
    stress: "breathing",
    massage: "massage"
};

const ICON_ALIASES: Record<string, string> = {
    sleep: "bed",
    water: "droplet",
    hydration: "droplet",
    nutrition: "meal",
    activity: "walk",
    recovery: "rest",
    stress: "breathing",
    massage: "massage"
};

let selectedHabitId:
    number | string | null = null;

let habits: RecoveryHabit[] = [];

let addedHabits:
    RecoveryHabit[] = [];

let sortMode: SortMode = "points";

let currentUserId:
    number | null = null;

let initialized = false;

function getElements():
    HabitModalElements | null {
    const backdrop =
        document.getElementById(
            "habit-modal-backdrop"
        );

    const list =
        document.getElementById(
            "habit-modal-list"
        );

    const openButton =
        document.getElementById(
            "open-habit-modal"
        );

    const backButton =
        document.getElementById(
            "habit-back-btn"
        ) as HTMLButtonElement | null;

    const saveButton =
        document.getElementById(
            "save-habit"
        ) as HTMLButtonElement | null;

    const sortButtons =
        document.querySelectorAll<HTMLButtonElement>(
            ".habit-sort-btn"
        );

    if (
        !backdrop ||
        !list ||
        !openButton ||
        !backButton ||
        !saveButton
    ) {
        return null;
    }

    return {
        backdrop,
        list,
        openButton,
        backButton,
        saveButton,
        sortButtons
    };
}

function getHabitId(
    habit: RecoveryHabit
): number | string | null {
    return (
        habit.id ??
        habit.habit_id ??
        habit.user_habit_id ??
        null
    );
}

function getUserHabitId(
    habit: UserHabit
): number | string | null {
    return (
        habit.habit_id ??
        habit.id ??
        habit.user_habit_id ??
        null
    );
}

function getHabitName(
    habit: RecoveryHabit
): string {
    return habit.name || "Звичка";
}

function getHabitPoints(
    habit: RecoveryHabit
): number {
    return habit.points ?? 0;
}

function getCategoryKey(
    category?: string | null
): string {
    return category || "recovery";
}

function getCategoryLabel(
    category?: string | null
): string {
    const key =
        getCategoryKey(
            category
        );

    return (
        CATEGORY_LABELS[key] ??
        category ??
        "Відновлення"
    );
}

function getCategoryColor(
    category?: string | null
): string {
    return (
        CATEGORY_COLORS[
            getCategoryKey(category)
        ] ??
        CATEGORY_COLORS.recovery
    );
}

function getCategoryBackground(
    category?: string | null
): string {
    return (
        CATEGORY_BACKGROUNDS[
            getCategoryKey(category)
        ] ??
        CATEGORY_BACKGROUNDS.recovery
    );
}

function getHabitIcon(
    habit: RecoveryHabit
): string {
    const category =
        getCategoryKey(
            habit.category
        );

    const requestedIcon =
        habit.icon?.trim() || "";

    let iconName =
        CATEGORY_ICONS[category] ||
        "rest";

    if (requestedIcon) {
        iconName =
            ICON_ALIASES[
                requestedIcon
            ] ||
            requestedIcon;
    }

    return (
        ICONS[
            iconName as keyof typeof ICONS
        ] ??
        ICONS.rest
    );
}

function normalizeHabits(
    data: unknown
): RecoveryHabit[] {
    if (Array.isArray(data)) {
        return data as RecoveryHabit[];
    }

    if (
        data &&
        typeof data === "object"
    ) {
        const value =
            data as {
                habits?: unknown;
                items?: unknown;
                data?: unknown;
            };

        if (
            Array.isArray(
                value.habits
            )
        ) {
            return value.habits as RecoveryHabit[];
        }

        if (
            Array.isArray(
                value.items
            )
        ) {
            return value.items as RecoveryHabit[];
        }

        if (
            Array.isArray(
                value.data
            )
        ) {
            return value.data as RecoveryHabit[];
        }
    }

    return [];
}

function normalizeUserHabits(
    data: unknown
): UserHabit[] {
    if (Array.isArray(data)) {
        return data as UserHabit[];
    }

    if (
        data &&
        typeof data === "object"
    ) {
        const value =
            data as {
                habits?: unknown;
                items?: unknown;
                data?: unknown;
            };

        if (
            Array.isArray(
                value.habits
            )
        ) {
            return value.habits as UserHabit[];
        }

        if (
            Array.isArray(
                value.items
            )
        ) {
            return value.items as UserHabit[];
        }

        if (
            Array.isArray(
                value.data
            )
        ) {
            return value.data as UserHabit[];
        }
    }

    return [];
}

function sortHabits(
    source: RecoveryHabit[]
): RecoveryHabit[] {
    const result = [...source];

    if (sortMode === "name") {
        return result.sort(
            (a, b) =>
                getHabitName(a).localeCompare(
                    getHabitName(b),
                    "uk"
                )
        );
    }

    if (sortMode === "category") {
        return result.sort(
            (a, b) =>
                getCategoryLabel(
                    a.category
                ).localeCompare(
                    getCategoryLabel(
                        b.category
                    ),
                    "uk"
                )
        );
    }

    return result.sort(
        (a, b) =>
            getHabitPoints(b) -
            getHabitPoints(a)
    );
}

function sortAddedHabits(
    source: RecoveryHabit[]
): RecoveryHabit[] {
    return [...source].sort(
        (a, b) =>
            getHabitName(a).localeCompare(
                getHabitName(b),
                "uk"
            )
    );
}

function createSectionTitle(
    text: string
): HTMLElement {
    const title =
        document.createElement(
            "div"
        );

    title.className =
        "habit-modal-section-title";

    title.textContent = text;

    return title;
}

function createEmptyState(
    text: string,
    secondary = false
): HTMLElement {
    const empty =
        document.createElement(
            "div"
        );

    empty.className =
        "habit-modal-empty";

    if (secondary) {
        empty.classList.add(
            "habit-modal-empty-secondary"
        );
    }

    empty.textContent = text;

    return empty;
}

function createHabitItem(
    habit: RecoveryHabit,
    elements: HabitModalElements,
    added = false
): HTMLElement {
    const item =
        document.createElement(
            "button"
        );

    item.type = "button";
    item.className = "habit-row";

    if (added) {
        item.classList.add(
            "habit-row-added"
        );
    }

    const habitId =
        getHabitId(habit);

    const isSelected =
        habitId !== null &&
        String(habitId) ===
            String(selectedHabitId);

    if (isSelected) {
        item.classList.add(
            "selected"
        );
    }

    const categoryColor =
        getCategoryColor(
            habit.category
        );

    const categoryBackground =
        getCategoryBackground(
            habit.category
        );

    item.style.setProperty(
        "--cat-color",
        categoryColor
    );

    item.style.setProperty(
        "--cat-color-bg",
        categoryBackground
    );

    const left =
        document.createElement(
            "span"
        );

    left.className =
        "habit-left";

    const icon =
        document.createElement(
            "span"
        );

    icon.className =
        "habit-modal-icon";

    icon.innerHTML =
        getHabitIcon(habit);

    const info =
        document.createElement(
            "span"
        );

    info.className =
        "habit-info";

    const title =
        document.createElement(
            "span"
        );

    title.className =
        "habit-title";

    title.textContent =
        getHabitName(habit);

    const description =
        document.createElement(
            "span"
        );

    description.className =
        "habit-description";

    description.textContent =
        habit.description ||
        getCategoryLabel(
            habit.category
        );

    info.appendChild(title);
    info.appendChild(description);

    left.appendChild(icon);
    left.appendChild(info);

    const right =
        document.createElement(
            "span"
        );

    right.className =
        "habit-right";

    const points =
        document.createElement(
            "span"
        );

    points.className =
        "habit-points";

    points.textContent =
        `Recovery +${getHabitPoints(habit)}`;

    const meta =
        document.createElement(
            "span"
        );

    meta.className =
        "habit-meta";

    meta.textContent =
        getCategoryLabel(
            habit.category
        );

    const check =
        document.createElement(
            "span"
        );

    check.className =
        "habit-check";

    if (
        added ||
        isSelected
    ) {
        check.classList.add(
            "checked"
        );

        check.textContent =
            "✓";
    }

    right.appendChild(points);
    right.appendChild(meta);
    right.appendChild(check);

    item.appendChild(left);
    item.appendChild(right);

    if (!added) {
        item.addEventListener(
            "click",
            () => {
                const currentlySelected =
                    habitId !== null &&
                    String(habitId) ===
                        String(selectedHabitId);

                if (
                    currentlySelected
                ) {
                    selectedHabitId =
                        null;
                } else {
                    selectedHabitId =
                        habitId;
                }

                elements.saveButton.disabled =
                    selectedHabitId ===
                    null;

                renderFullList(
                    elements,
                    habits,
                    addedHabits
                );
            }
        );
    }

    return item;
}

function renderFullList(
    elements: HabitModalElements,
    available: RecoveryHabit[],
    added: RecoveryHabit[]
): void {
    elements.list.innerHTML = "";

    const sortedAvailable =
        sortHabits(available);

    const sortedAdded =
        sortAddedHabits(added);

    elements.list.appendChild(
        createSectionTitle(
            "Доступні звички"
        )
    );

    if (
        sortedAvailable.length ===
        0
    ) {
        elements.list.appendChild(
            createEmptyState(
                "Усі доступні звички вже додані"
            )
        );
    } else {
        sortedAvailable.forEach(
            habit => {
                elements.list.appendChild(
                    createHabitItem(
                        habit,
                        elements
                    )
                );
            }
        );
    }

    elements.list.appendChild(
        createSectionTitle(
            "Вже додані"
        )
    );

    if (
        sortedAdded.length ===
        0
    ) {
        elements.list.appendChild(
            createEmptyState(
                "Ще немає доданих звичок",
                true
            )
        );
    } else {
        sortedAdded.forEach(
            habit => {
                elements.list.appendChild(
                    createHabitItem(
                        habit,
                        elements,
                        true
                    )
                );
            }
        );
    }
}

function openModal(
    elements: HabitModalElements
): void {
    selectedHabitId = null;

    elements.saveButton.disabled =
        true;

    elements.backdrop.hidden =
        false;

    requestAnimationFrame(() => {
        elements.backdrop.classList.add(
            "open"
        );
    });

    document.body.classList.add(
        "modal-open"
    );

    void loadHabits(
        elements
    );
}

function closeModal(
    elements: HabitModalElements
): void {
    elements.backdrop.classList.remove(
        "open"
    );

    window.setTimeout(
        () => {
            if (
                !elements.backdrop.classList.contains(
                    "open"
                )
            ) {
                elements.backdrop.hidden =
                    true;
            }
        },
        180
    );

    document.body.classList.remove(
        "modal-open"
    );

    selectedHabitId = null;

    elements.saveButton.disabled =
        true;
}

async function loadHabits(
    elements: HabitModalElements
): Promise<void> {
    elements.list.innerHTML = "";

    const loading =
        document.createElement(
            "div"
        );

    loading.className =
        "habit-modal-loading";

    loading.textContent =
        "Завантаження...";

    elements.list.appendChild(
        loading
    );

    if (
        currentUserId === null
    ) {
        return;
    }

    try {
        const [
            allHabitsPayload,
            userHabitsPayload
        ] = await Promise.all([
            RecoveryAPI.getHabitsList(),
            RecoveryAPI.getUserHabits(
                currentUserId
            )
        ]);

        const allHabits =
            normalizeHabits(
                allHabitsPayload
            );

        const userHabits =
            normalizeUserHabits(
                userHabitsPayload
            );

        const userHabitIds =
            new Set(
                userHabits
                    .map(
                        getUserHabitId
                    )
                    .filter(
                        id =>
                            id !== null
                    )
                    .map(
                        id =>
                            String(id)
                    )
            );

        const available =
            allHabits.filter(
                habit => {
                    const habitId =
                        getHabitId(
                            habit
                        );

                    return (
                        habitId !== null &&
                        !userHabitIds.has(
                            String(habitId)
                        )
                    );
                }
            );

        const added =
            allHabits.filter(
                habit => {
                    const habitId =
                        getHabitId(
                            habit
                        );

                    return (
                        habitId !== null &&
                        userHabitIds.has(
                            String(habitId)
                        )
                    );
                }
            );

        habits = available;
        addedHabits = added;

        renderFullList(
            elements,
            habits,
            addedHabits
        );
    } catch {
        elements.list.innerHTML = "";

        const error =
            document.createElement(
                "div"
            );

        error.className =
            "habit-modal-error";

        error.textContent =
            "Не вдалося завантажити звички";

        elements.list.appendChild(
            error
        );
    }
}

async function saveHabit(
    elements: HabitModalElements
): Promise<void> {
    if (
        currentUserId === null ||
        selectedHabitId === null
    ) {
        return;
    }

    elements.saveButton.disabled =
        true;

    try {
        await RecoveryAPI.addHabit(
            currentUserId,
            selectedHabitId
        );

        closeModal(elements);

        await refreshRecoveryDashboard(
            currentUserId
        );
    } catch {
        elements.saveButton.disabled =
            false;
    }
}

function setSortMode(
    mode: SortMode,
    elements: HabitModalElements
): void {
    sortMode = mode;

    elements.sortButtons.forEach(
        button => {
            button.classList.toggle(
                "active",
                button.dataset.sort ===
                    mode
            );
        }
    );

    renderFullList(
        elements,
        habits,
        addedHabits
    );
}

export function initHabitModal(
    userId: number
): void {
    if (initialized) {
        return;
    }

    const elements =
        getElements();

    if (!elements) {
        return;
    }

    initialized = true;
    currentUserId = userId;

    elements.openButton.addEventListener(
        "click",
        () => {
            openModal(elements);
        }
    );

    elements.backButton.addEventListener(
        "click",
        () => {
            closeModal(elements);
        }
    );

    elements.saveButton.addEventListener(
        "click",
        () => {
            void saveHabit(
                elements
            );
        }
    );

    elements.sortButtons.forEach(
        button => {
            button.addEventListener(
                "click",
                () => {
                    const mode =
                        button.dataset.sort;

                    if (
                        mode === "points" ||
                        mode === "category" ||
                        mode === "name"
                    ) {
                        setSortMode(
                            mode,
                            elements
                        );
                    }
                }
            );
        }
    );

    elements.backdrop.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                elements.backdrop
            ) {
                closeModal(
                    elements
                );
            }
        }
    );
}