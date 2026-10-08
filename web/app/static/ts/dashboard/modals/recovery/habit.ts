import {
    dashboard_t,
    getLocale,
    recovery_t
} from "../../../i18n/index.js";

import { ICONS } from "../../../icons/index.js";
import { RecoveryAPI } from "./api.js";

import {
    refreshRecoveryWidget
} from "../../widgets/recovery/index.js";

interface Habit {
    id: number;
    slug?: string;
    name: string;
    description?: string;
    category?: string;
    icon?: string;
    points?: number;
}

interface UserHabit {
    id?: number;
    habit_id?: number;
    user_habit_id?: number;
}

const CATEGORY_KEYS: Record<string, string> = {
    hydration: "hydration",
    sleep: "sleep",
    nutrition: "nutrition",
    activity: "activity",
    recovery: "recovery",
    stress: "stress",
    massage: "massage"
};

let initialized = false;
let currentSort = "points";

function normalizeHabits(
    payload: unknown
): Habit[] {
    if (Array.isArray(payload)) {
        return payload as Habit[];
    }

    if (
        typeof payload === "object" &&
        payload !== null
    ) {
        const value =
            payload as Record<string, unknown>;

        if (Array.isArray(value.habits)) {
            return value.habits as Habit[];
        }

        if (Array.isArray(value.items)) {
            return value.items as Habit[];
        }

        if (Array.isArray(value.data)) {
            return value.data as Habit[];
        }
    }

    return [];
}

function normalizeUserHabits(
    payload: unknown
): UserHabit[] {
    if (Array.isArray(payload)) {
        return payload as UserHabit[];
    }

    if (
        typeof payload === "object" &&
        payload !== null
    ) {
        const value =
            payload as Record<string, unknown>;

        if (Array.isArray(value.habits)) {
            return value.habits as UserHabit[];
        }

        if (Array.isArray(value.items)) {
            return value.items as UserHabit[];
        }

        if (Array.isArray(value.data)) {
            return value.data as UserHabit[];
        }
    }

    return [];
}

function getHabitId(
    habit: UserHabit
): number {
    return Number(
        habit.habit_id ??
        habit.id ??
        habit.user_habit_id ??
        0
    );
}

function getIcon(
    iconKey?: string
): string {
    if (!iconKey) {
        return ICONS.rest;
    }

    const icons =
        ICONS as Record<string, string>;

    return icons[iconKey] || ICONS.rest;
}

function getHabitName(
    habit: Habit
): string {
    const slug =
        habit.slug?.trim();

    if (slug) {
        const key =
            `habits.${slug}.name`;

        const translated =
            recovery_t(key);

        if (translated !== key) {
            return translated;
        }
    }

    return habit.name || "";
}

function getHabitDescription(
    habit: Habit
): string {
    const slug =
        habit.slug?.trim();

    if (slug) {
        const key =
            `habits.${slug}.description`;

        const translated =
            recovery_t(key);

        if (translated !== key) {
            return translated;
        }
    }

    return habit.description || "";
}

function localizeCategory(
    category?: string
): string {
    if (!category) {
        return "";
    }

    const key =
        CATEGORY_KEYS[category];

    if (!key) {
        return category;
    }

    const translationKey =
        `categories.${key}`;

    const translated =
        recovery_t(translationKey);

    if (translated !== translationKey) {
        return translated;
    }

    return category;
}

function getRecoveryImpact(
    points?: number
): string {
    return `${recovery_t(
        "points.label"
    )} +${Number(points || 0)}`;
}

function sortAvailable(
    habits: Habit[],
    sortKey: string
): Habit[] {
    const sorted = [...habits];

    if (sortKey === "points") {
        return sorted.sort(
            (a, b) =>
                Number(b.points || 0) -
                Number(a.points || 0)
        );
    }

    if (sortKey === "category") {
        return sorted.sort(
            (a, b) =>
                localizeCategory(
                    a.category
                ).localeCompare(
                    localizeCategory(
                        b.category
                    ),
                    getLocale()
                )
        );
    }

    if (sortKey === "name") {
        return sorted.sort(
            (a, b) =>
                getHabitName(a).localeCompare(
                    getHabitName(b),
                    getLocale()
                )
        );
    }

    return sorted;
}

function sortAdded(
    habits: Habit[]
): Habit[] {
    return [...habits].sort(
        (a, b) =>
            getHabitName(a).localeCompare(
                getHabitName(b),
                getLocale()
            )
    );
}

function createHabitRow(
    habit: Habit,
    added: boolean,
    selected: Set<number>
): HTMLElement {
    const category =
        habit.category ||
        "recovery";

    const row =
        document.createElement("div");

    row.className =
        "dashboard-habit-row";

    if (category) {
        row.classList.add(
            `dashboard-habit-cat-${category}`
        );
    }

    if (added) {
        row.classList.add(
            "dashboard-habit-added"
        );
    }

    row.dataset.habitId =
        String(habit.id);

    const left =
        document.createElement("div");

    left.className =
        "dashboard-habit-left";

    const icon =
        document.createElement("div");

    icon.className =
        "dashboard-habit-modal-icon";

    icon.innerHTML =
        getIcon(habit.icon);

    const info =
        document.createElement("div");

    info.className =
        "dashboard-habit-info";

    const title =
        document.createElement("div");

    title.className =
        "dashboard-habit-title";

    title.textContent =
        getHabitName(habit);

    info.appendChild(title);

    const descriptionText =
        getHabitDescription(habit);

    if (descriptionText) {
        const description =
            document.createElement("div");

        description.className =
            "dashboard-habit-description";

        description.textContent =
            descriptionText;

        info.appendChild(
            description
        );
    }

    left.appendChild(icon);
    left.appendChild(info);

    const right =
        document.createElement("div");

    right.className =
        "dashboard-habit-right";

    const impact =
        document.createElement("div");

    impact.className =
        "dashboard-habit-impact";

    impact.textContent =
        getRecoveryImpact(
            habit.points
        );

    const meta =
        document.createElement("div");

    meta.className =
        "dashboard-habit-meta";

    meta.textContent =
        localizeCategory(
            category
        );

    const check =
        document.createElement("div");

    check.className =
        "dashboard-habit-check";

    if (
        added ||
        selected.has(habit.id)
    ) {
        check.classList.add(
            "dashboard-habit-checked"
        );

        check.textContent =
            "✓";
    }

    right.appendChild(impact);
    right.appendChild(meta);
    right.appendChild(check);

    row.appendChild(left);
    row.appendChild(right);

    return row;
}

export function initHabitModal(
    userId: number
): void {
    if (initialized) {
        return;
    }

    if (
        !Number.isFinite(userId) ||
        userId <= 0
    ) {
        console.error(
            "Invalid recovery user ID:",
            userId
        );

        return;
    }

    /*
     * Support the current dashboard modal
     * selectors while keeping the original
     * modal markup compatible.
     */
    const backdropElement =
        document.querySelector<HTMLElement>(
            "#dashboard-habit-modal"
        ) ||
        document.querySelector<HTMLElement>(
            "#habit-modal-backdrop"
        );

    const openButtonElement =
        document.querySelector<HTMLElement>(
            "#dashboard-open-habit-modal"
        ) ||
        document.querySelector<HTMLElement>(
            "#dashboard-open-recovery"
        );

    const backButtonElement =
        document.querySelector<HTMLButtonElement>(
            "#habit-back-btn"
        ) ||
        document.querySelector<HTMLButtonElement>(
            ".dashboard-habit-close"
        );

    const saveButtonElement =
        document.querySelector<HTMLButtonElement>(
            "#save-habit"
        ) ||
        document.querySelector<HTMLButtonElement>(
            ".dashboard-habit-save"
        );

    const listBoxElement =
        document.querySelector<HTMLElement>(
            "#habit-modal-list"
        ) ||
        document.querySelector<HTMLElement>(
            ".dashboard-habit-list"
        );

    const sortButtons =
        document.querySelectorAll<HTMLButtonElement>(
            ".dashboard-habit-sort-btn"
        );

    if (
        !(backdropElement instanceof HTMLElement) ||
        !(openButtonElement instanceof HTMLElement) ||
        !(backButtonElement instanceof HTMLButtonElement) ||
        !(saveButtonElement instanceof HTMLButtonElement) ||
        !(listBoxElement instanceof HTMLElement)
    ) {
        console.error(
            "Recovery habit modal elements not found"
        );

        return;
    }

    /*
     * Keep stable non-null references for nested
     * functions and callbacks.
     */
    const backdrop =
        backdropElement;

    const openButton =
        openButtonElement;

    const backButton =
        backButtonElement;

    const saveButton =
        saveButtonElement;

    const listBox =
        listBoxElement;

    initialized = true;

    function updateSaveState(): void {
        const selected =
            listBox.querySelectorAll(
                ".dashboard-habit-row.dashboard-habit-selected"
            );

        saveButton.disabled =
            selected.length === 0;
    }

    async function renderList(): Promise<void> {
        listBox.innerHTML = "";

        const loading =
            document.createElement("div");

        loading.className =
            "dashboard-habit-loading";

        loading.textContent =
            dashboard_t(
                "recovery.habitModal.loading"
            );

        listBox.appendChild(
            loading
        );

        try {
            const [
                habitsPayload,
                userHabitsPayload
            ] = await Promise.all([
                RecoveryAPI.getHabitsList(),
                RecoveryAPI.getUserHabits(
                    userId
                )
            ]);

            const habits =
                normalizeHabits(
                    habitsPayload
                );

            const userHabits =
                normalizeUserHabits(
                    userHabitsPayload
                );

            const userHabitIds =
                new Set(
                    userHabits
                        .map(getHabitId)
                        .filter(
                            id => id > 0
                        )
                );

            const available =
                sortAvailable(
                    habits.filter(
                        habit =>
                            !userHabitIds.has(
                                Number(
                                    habit.id
                                )
                            )
                    ),
                    currentSort
                );

            const added =
                sortAdded(
                    habits.filter(
                        habit =>
                            userHabitIds.has(
                                Number(
                                    habit.id
                                )
                            )
                    )
                );

            listBox.innerHTML = "";

            const availableHeader =
                document.createElement("div");

            availableHeader.className =
                "dashboard-habit-section-title";

            availableHeader.textContent =
                dashboard_t(
                    "recovery.habitModal.available"
                );

            listBox.appendChild(
                availableHeader
            );

            if (
                available.length === 0
            ) {
                const empty =
                    document.createElement(
                        "div"
                    );

                empty.className =
                    "dashboard-habit-empty";

                empty.textContent =
                    dashboard_t(
                        "recovery.habitModal.emptyAvailable"
                    );

                listBox.appendChild(
                    empty
                );
            } else {
                available.forEach(
                    habit => {
                        listBox.appendChild(
                            createHabitRow(
                                habit,
                                false,
                                new Set<number>()
                            )
                        );
                    }
                );
            }

            const addedHeader =
                document.createElement("div");

            addedHeader.className =
                "dashboard-habit-section-title";

            addedHeader.textContent =
                dashboard_t(
                    "recovery.habitModal.alreadyAdded"
                );

            listBox.appendChild(
                addedHeader
            );

            if (
                added.length === 0
            ) {
                const empty =
                    document.createElement(
                        "div"
                    );

                empty.className =
                    "dashboard-habit-empty dashboard-habit-empty-secondary";

                empty.textContent =
                    dashboard_t(
                        "recovery.habitModal.emptyAdded"
                    );

                listBox.appendChild(
                    empty
                );
            } else {
                added.forEach(
                    habit => {
                        listBox.appendChild(
                            createHabitRow(
                                habit,
                                true,
                                new Set<number>()
                            )
                        );
                    }
                );
            }

            updateSaveState();
        } catch (error) {
            console.error(
                "Failed to load recovery habits:",
                error
            );

            listBox.innerHTML = "";

            const errorBox =
                document.createElement(
                    "div"
                );

            errorBox.className =
                "dashboard-habit-error";

            errorBox.textContent =
                dashboard_t(
                    "recovery.habitModal.loadFailed"
                );

            listBox.appendChild(
                errorBox
            );

            updateSaveState();
        }
    }

    function open(): void {
        backdrop.hidden = false;

        requestAnimationFrame(
            () => {
                backdrop.classList.add(
                    "open"
                );
            }
        );

        saveButton.disabled = true;

        void renderList();
    }

    function close(): void {
        backdrop.classList.remove(
            "open"
        );

        window.setTimeout(
            () => {
                if (
                    !backdrop.classList.contains(
                        "open"
                    )
                ) {
                    backdrop.hidden = true;
                }
            },
            180
        );

        listBox.innerHTML = "";

        saveButton.disabled = true;
    }

    async function save(): Promise<void> {
        const selected =
            Array.from(
                listBox.querySelectorAll<HTMLElement>(
                    ".dashboard-habit-row.dashboard-habit-selected"
                )
            );

        if (
            selected.length === 0
        ) {
            return;
        }

        saveButton.disabled = true;

        try {
            const habitIds =
                selected
                    .map(
                        row =>
                            Number(
                                row.dataset.habitId
                            )
                    )
                    .filter(
                        id =>
                            Number.isFinite(id) &&
                            id > 0
                    );

            if (
                habitIds.length === 0
            ) {
                throw new Error(
                    "No valid habit IDs selected"
                );
            }

            await Promise.all(
                habitIds.map(
                    habitId =>
                        RecoveryAPI.addHabit(
                            userId,
                            habitId
                        )
                )
            );

            await refreshRecoveryWidget();

            window.dispatchEvent(
                new CustomEvent(
                    "dashboard:refresh"
                )
            );

            close();
        } catch (error) {
            console.error(
                "Failed to save recovery habits:",
                error
            );

            alert(
                dashboard_t(
                    "recovery.habitModal.saveFailed"
                )
            );

            saveButton.disabled =
                false;
        }
    }

    openButton.addEventListener(
        "click",
        open
    );

    backButton.addEventListener(
        "click",
        close
    );

    saveButton.addEventListener(
        "click",
        () => {
            void save();
        }
    );

    backdrop.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                backdrop
            ) {
                close();
            }
        }
    );

    /*
     * Keep the original event delegation:
     * selecting a habit must work when clicking
     * anywhere inside the row.
     */
    listBox.addEventListener(
        "click",
        event => {
            const target =
                event.target;

            if (
                !(target instanceof HTMLElement)
            ) {
                return;
            }

            const row =
                target.closest<HTMLElement>(
                    ".dashboard-habit-row"
                );

            if (!row) {
                return;
            }

            /*
             * Already added habits are displayed
             * but cannot be selected again.
             */
            if (
                row.classList.contains(
                    "dashboard-habit-added"
                )
            ) {
                return;
            }

            row.classList.toggle(
                "dashboard-habit-selected"
            );

            /*
             * Keep the visual checked state
             * synchronized with the selected state.
             */
            const check =
                row.querySelector<HTMLElement>(
                    ".dashboard-habit-check"
                );

            if (check) {
                const checked =
                    row.classList.contains(
                        "dashboard-habit-selected"
                    );

                check.classList.toggle(
                    "dashboard-habit-checked",
                    checked
                );

                check.textContent =
                    checked
                        ? "✓"
                        : "";
            }

            updateSaveState();
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape" &&
                !backdrop.hidden
            ) {
                close();
            }
        }
    );

    sortButtons.forEach(
        button => {
            button.addEventListener(
                "click",
                () => {
                    sortButtons.forEach(
                        item =>
                            item.classList.remove(
                                "active"
                            )
                    );

                    button.classList.add(
                        "active"
                    );

                    currentSort =
                        button.dataset.sort ||
                        "points";

                    void renderList();
                }
            );
        }
    );
}