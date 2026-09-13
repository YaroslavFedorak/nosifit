import { DashboardAPI } from "../../api.js";

interface Habit {
    id: number;
    name: string;
    description?: string;
    category?: string;
    icon?: string;
    points?: number;
}

interface UserHabit {
    id: number;
}

type SortKey =
    | "points"
    | "category"
    | "name";

let initialized = false;
let currentSort: SortKey = "points";

const CATEGORY_MAP: Record<string, string> = {
    hydration: "Вода",
    sleep: "Сон",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};

function getElement<T extends HTMLElement>(
    selector: string
): T | null {
    return document.querySelector<T>(selector);
}

function getUserId(): string | null {
    const root = document.querySelector<HTMLElement>(
        ".dashboard-page-wrapper"
    );

    return root?.dataset.userId || null;
}

function localizeCategory(
    category?: string
): string {
    if (!category) {
        return "";
    }

    return CATEGORY_MAP[category] || category;
}

function getIcon(habit: Habit): string {
    const icons = (
        window as Window & {
            ICONS?: Record<string, string>;
        }
    ).ICONS;

    return (
        icons?.[habit.icon || "rest"] ||
        icons?.rest ||
        ""
    );
}

function sortHabits(
    habits: Habit[],
    sort: SortKey
): Habit[] {
    const result = [...habits];

    if (sort === "points") {
        return result.sort(
            (a, b) =>
                Number(b.points || 0) -
                Number(a.points || 0)
        );
    }

    if (sort === "category") {
        return result.sort((a, b) =>
            localizeCategory(a.category).localeCompare(
                localizeCategory(b.category),
                "uk"
            )
        );
    }

    return result.sort((a, b) =>
        a.name.localeCompare(
            b.name,
            "uk"
        )
    );
}

function createHabitRow(
    habit: Habit,
    added: boolean
): HTMLElement {
    const category =
        habit.category || "recovery";

    const row = document.createElement("div");

    row.className =
        `habit-row habit-cat-${category}`;

    if (added) {
        row.classList.add("habit-added");
    }

    row.dataset.habitId =
        String(habit.id);

    const left =
        document.createElement("div");

    left.className = "habit-left";

    const icon =
        document.createElement("div");

    icon.className =
        "habit-modal-icon";

    icon.innerHTML =
        getIcon(habit);

    const info =
        document.createElement("div");

    info.className =
        "habit-info";

    const title =
        document.createElement("div");

    title.className =
        "habit-title";

    title.textContent =
        habit.name;

    info.appendChild(title);

    if (habit.description) {
        const description =
            document.createElement("div");

        description.className =
            "habit-description";

        description.textContent =
            habit.description;

        info.appendChild(description);
    }

    left.appendChild(icon);
    left.appendChild(info);

    const right =
        document.createElement("div");

    right.className =
        "habit-right";

    const points =
        document.createElement("div");

    points.className =
        "habit-points";

    points.textContent =
        `Recovery +${Number(habit.points || 0)}`;

    const meta =
        document.createElement("div");

    meta.className =
        "habit-meta";

    meta.textContent =
        localizeCategory(category);

    const check =
        document.createElement("div");

    check.className =
        "habit-check";

    if (added) {
        check.classList.add("checked");
        check.textContent = "✓";
    }

    right.appendChild(points);
    right.appendChild(meta);
    right.appendChild(check);

    row.appendChild(left);
    row.appendChild(right);

    return row;
}

async function loadHabits(
    userId: string
): Promise<void> {
    const list =
        getElement<HTMLElement>(
            "#dashboard-habit-modal-list"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "#dashboard-save-habit"
        );

    if (!list || !saveButton) {
        return;
    }

    list.textContent =
        "Завантаження…";

    try {
        const [
            allHabits,
            userHabits
        ] = await Promise.all([
            DashboardAPI.getRecoveryHabits(),
            DashboardAPI.getUserRecoveryHabits(
                userId
            )
        ]);

        const userHabitIds =
            new Set(
                userHabits.map(
                    (habit: UserHabit) =>
                        habit.id
                )
            );

        const available =
            allHabits.filter(
                (habit: Habit) =>
                    !userHabitIds.has(
                        habit.id
                    )
            );

        const added =
            allHabits.filter(
                (habit: Habit) =>
                    userHabitIds.has(
                        habit.id
                    )
            );

        const sortedAvailable =
            sortHabits(
                available,
                currentSort
            );

        const sortedAdded =
            [...added].sort((a, b) =>
                a.name.localeCompare(
                    b.name,
                    "uk"
                )
            );

        list.replaceChildren();

        const availableHeader =
            document.createElement("div");

        availableHeader.className =
            "habit-section-title";

        availableHeader.textContent =
            "Доступні";

        list.appendChild(
            availableHeader
        );

        if (sortedAvailable.length === 0) {
            const empty =
                document.createElement("div");

            empty.className =
                "habit-empty";

            empty.textContent =
                "Усі доступні звички вже додані";

            list.appendChild(empty);
        } else {
            sortedAvailable.forEach(
                (habit) => {
                    list.appendChild(
                        createHabitRow(
                            habit,
                            false
                        )
                    );
                }
            );
        }

        const addedHeader =
            document.createElement("div");

        addedHeader.className =
            "habit-section-title";

        addedHeader.textContent =
            "Вже додані";

        list.appendChild(
            addedHeader
        );

        sortedAdded.forEach(
            (habit) => {
                list.appendChild(
                    createHabitRow(
                        habit,
                        true
                    )
                );
            }
        );

        updateSaveState();
    } catch (error) {
        console.error(
            "Failed to load habits:",
            error
        );

        list.textContent =
            "Не вдалося завантажити звички";
    }
}

function updateSaveState(): void {
    const list =
        getElement<HTMLElement>(
            "#dashboard-habit-modal-list"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "#dashboard-save-habit"
        );

    if (!list || !saveButton) {
        return;
    }

    const selected =
        list.querySelectorAll(
            ".habit-row.selected"
        );

    saveButton.disabled =
        selected.length === 0;
}

function openModal(): void {
    const backdrop =
        getElement<HTMLElement>(
            "#habit-modal-backdrop"
        );

    const userId =
        getUserId();

    if (!backdrop || !userId) {
        return;
    }

    backdrop.classList.add("open");

    loadHabits(userId);
}

function closeModal(): void {
    const backdrop =
        getElement<HTMLElement>(
            "#habit-modal-backdrop"
        );

    const list =
        getElement<HTMLElement>(
            "#dashboard-habit-modal-list"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "#dashboard-save-habit"
        );

    backdrop?.classList.remove("open");

    list?.replaceChildren();

    if (saveButton) {
        saveButton.disabled = true;
    }
}

async function saveHabits(): Promise<void> {
    const userId =
        getUserId();

    const list =
        getElement<HTMLElement>(
            "#dashboard-habit-modal-list"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "#dashboard-save-habit"
        );

    if (!userId || !list || !saveButton) {
        return;
    }

    const selected =
        Array.from(
            list.querySelectorAll<HTMLElement>(
                ".habit-row.selected"
            )
        );

    if (selected.length === 0) {
        return;
    }

    saveButton.disabled = true;

    try {
        await Promise.all(
            selected.map((row) =>
                DashboardAPI.addRecoveryHabit(
                    userId,
                    Number(row.dataset.habitId)
                )
            )
        );

        closeModal();

        window.dispatchEvent(
            new CustomEvent(
                "dashboard:recovery-updated"
            )
        );
    } catch (error) {
        console.error(
            "Failed to save habits:",
            error
        );

        alert(
            error instanceof Error
                ? error.message
                : "Не вдалося додати звички"
        );

        saveButton.disabled = false;
    }
}

export function initHabitModal(): void {
    if (initialized) {
        return;
    }

    const openButton =
        getElement<HTMLButtonElement>(
            "#dashboard-add-habit"
        );

    const backButton =
        getElement<HTMLButtonElement>(
            "#dashboard-habit-back"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "#dashboard-save-habit"
        );

    const list =
        getElement<HTMLElement>(
            "#dashboard-habit-modal-list"
        );

    const backdrop =
        getElement<HTMLElement>(
            "#habit-modal-backdrop"
        );

    if (
        !openButton ||
        !backButton ||
        !saveButton ||
        !list ||
        !backdrop
    ) {
        return;
    }

    initialized = true;

    openButton.addEventListener(
        "click",
        openModal
    );

    backButton.addEventListener(
        "click",
        closeModal
    );

    saveButton.addEventListener(
        "click",
        saveHabits
    );

    list.addEventListener(
        "click",
        (event) => {
            const target =
                event.target;

            if (!(target instanceof HTMLElement)) {
                return;
            }

            const row =
                target.closest<HTMLElement>(
                    ".habit-row"
                );

            if (!row) {
                return;
            }

            if (
                row.classList.contains(
                    "habit-added"
                )
            ) {
                return;
            }

            row.classList.toggle(
                "selected"
            );

            const check =
                row.querySelector(
                    ".habit-check"
                );

            if (check) {
                const selected =
                    row.classList.contains(
                        "selected"
                    );

                check.classList.toggle(
                    "checked",
                    selected
                );

                check.textContent =
                    selected
                        ? "✓"
                        : "";
            }

            updateSaveState();
        }
    );

    document
        .querySelectorAll<HTMLButtonElement>(
            ".dashboard-habit-sort-btn"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                async () => {
                    const sort =
                        button.dataset.sort;

                    if (
                        sort !== "points" &&
                        sort !== "category" &&
                        sort !== "name"
                    ) {
                        return;
                    }

                    currentSort =
                        sort;

                    document
                        .querySelectorAll(
                            ".dashboard-habit-sort-btn"
                        )
                        .forEach(
                            (item) =>
                                item.classList.remove(
                                    "active"
                                )
                        );

                    button.classList.add(
                        "active"
                    );

                    const userId =
                        getUserId();

                    if (userId) {
                        await loadHabits(
                            userId
                        );
                    }
                }
            );
        });

    backdrop.addEventListener(
        "click",
        (event) => {
            if (event.target === backdrop) {
                closeModal();
            }
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape" &&
                backdrop.classList.contains("open")
            ) {
                closeModal();
            }
        }
    );
}