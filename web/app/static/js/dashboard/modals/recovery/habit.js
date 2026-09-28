import { dashboard_t, getLocale, recovery_t } from "../../../i18n/index.js";
import { ICONS } from "../../../icons/index.js";
import { RecoveryAPI } from "./api.js";
import { refreshRecoveryWidget } from "../../widgets/recovery/index.js";
const CATEGORY_KEYS = {
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
function normalizeHabits(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (typeof payload === "object" &&
        payload !== null) {
        const value = payload;
        if (Array.isArray(value.habits)) {
            return value.habits;
        }
        if (Array.isArray(value.items)) {
            return value.items;
        }
        if (Array.isArray(value.data)) {
            return value.data;
        }
    }
    return [];
}
function normalizeUserHabits(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (typeof payload === "object" &&
        payload !== null) {
        const value = payload;
        if (Array.isArray(value.habits)) {
            return value.habits;
        }
        if (Array.isArray(value.items)) {
            return value.items;
        }
        if (Array.isArray(value.data)) {
            return value.data;
        }
    }
    return [];
}
function getHabitId(habit) {
    return Number(habit.habit_id ??
        habit.id ??
        habit.user_habit_id ??
        0);
}
function getIcon(iconKey) {
    if (!iconKey) {
        return ICONS.rest;
    }
    const icons = ICONS;
    return icons[iconKey] || ICONS.rest;
}
function getHabitName(habit) {
    const slug = habit.slug?.trim();
    if (slug) {
        const key = `habits.${slug}.name`;
        const translated = recovery_t(key);
        if (translated !== key) {
            return translated;
        }
    }
    return habit.name || "";
}
function getHabitDescription(habit) {
    const slug = habit.slug?.trim();
    if (slug) {
        const key = `habits.${slug}.description`;
        const translated = recovery_t(key);
        if (translated !== key) {
            return translated;
        }
    }
    return habit.description || "";
}
function localizeCategory(category) {
    if (!category) {
        return "";
    }
    const key = CATEGORY_KEYS[category];
    if (!key) {
        return category;
    }
    const translationKey = `categories.${key}`;
    const translated = recovery_t(translationKey);
    if (translated !== translationKey) {
        return translated;
    }
    return category;
}
function getRecoveryImpact(points) {
    return `${recovery_t("points.label")} +${Number(points || 0)}`;
}
function sortAvailable(habits, sortKey) {
    const sorted = [...habits];
    if (sortKey === "points") {
        return sorted.sort((a, b) => Number(b.points || 0) -
            Number(a.points || 0));
    }
    if (sortKey === "category") {
        return sorted.sort((a, b) => localizeCategory(a.category).localeCompare(localizeCategory(b.category), getLocale()));
    }
    if (sortKey === "name") {
        return sorted.sort((a, b) => getHabitName(a).localeCompare(getHabitName(b), getLocale()));
    }
    return sorted;
}
function sortAdded(habits) {
    return [...habits].sort((a, b) => getHabitName(a).localeCompare(getHabitName(b), getLocale()));
}
function createHabitRow(habit, added, selected) {
    const category = habit.category ||
        "recovery";
    const row = document.createElement("div");
    row.className =
        "dashboard-habit-row";
    if (category) {
        row.classList.add(`dashboard-habit-cat-${category}`);
    }
    if (added) {
        row.classList.add("dashboard-habit-added");
    }
    row.dataset.habitId =
        String(habit.id);
    const left = document.createElement("div");
    left.className =
        "dashboard-habit-left";
    const icon = document.createElement("div");
    icon.className =
        "dashboard-habit-modal-icon";
    icon.innerHTML =
        getIcon(habit.icon);
    const info = document.createElement("div");
    info.className =
        "dashboard-habit-info";
    const title = document.createElement("div");
    title.className =
        "dashboard-habit-title";
    title.textContent =
        getHabitName(habit);
    info.appendChild(title);
    const descriptionText = getHabitDescription(habit);
    if (descriptionText) {
        const description = document.createElement("div");
        description.className =
            "dashboard-habit-description";
        description.textContent =
            descriptionText;
        info.appendChild(description);
    }
    left.appendChild(icon);
    left.appendChild(info);
    const right = document.createElement("div");
    right.className =
        "dashboard-habit-right";
    const impact = document.createElement("div");
    impact.className =
        "dashboard-habit-impact";
    impact.textContent =
        getRecoveryImpact(habit.points);
    const meta = document.createElement("div");
    meta.className =
        "dashboard-habit-meta";
    meta.textContent =
        localizeCategory(category);
    const check = document.createElement("div");
    check.className =
        "dashboard-habit-check";
    if (added ||
        selected.has(habit.id)) {
        check.classList.add("dashboard-habit-checked");
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
export function initHabitModal(userId) {
    if (initialized) {
        return;
    }
    if (!Number.isFinite(userId) ||
        userId <= 0) {
        console.error("Invalid recovery user ID:", userId);
        return;
    }
    /*
     * Support the current dashboard modal
     * selectors while keeping the original
     * modal markup compatible.
     */
    const backdropElement = document.querySelector("#dashboard-habit-modal") ||
        document.querySelector("#habit-modal-backdrop");
    const openButtonElement = document.querySelector("#dashboard-open-habit-modal") ||
        document.querySelector("#dashboard-open-recovery");
    const backButtonElement = document.querySelector("#habit-back-btn") ||
        document.querySelector(".dashboard-habit-close");
    const saveButtonElement = document.querySelector("#save-habit") ||
        document.querySelector(".dashboard-habit-save");
    const listBoxElement = document.querySelector("#habit-modal-list") ||
        document.querySelector(".dashboard-habit-list");
    const sortButtons = document.querySelectorAll(".dashboard-habit-sort-btn");
    if (!(backdropElement instanceof HTMLElement) ||
        !(openButtonElement instanceof HTMLElement) ||
        !(backButtonElement instanceof HTMLButtonElement) ||
        !(saveButtonElement instanceof HTMLButtonElement) ||
        !(listBoxElement instanceof HTMLElement)) {
        console.error("Recovery habit modal elements not found");
        return;
    }
    /*
     * Keep stable non-null references for nested
     * functions and callbacks.
     */
    const backdrop = backdropElement;
    const openButton = openButtonElement;
    const backButton = backButtonElement;
    const saveButton = saveButtonElement;
    const listBox = listBoxElement;
    initialized = true;
    function updateSaveState() {
        const selected = listBox.querySelectorAll(".dashboard-habit-row.dashboard-habit-selected");
        saveButton.disabled =
            selected.length === 0;
    }
    async function renderList() {
        listBox.innerHTML = "";
        const loading = document.createElement("div");
        loading.className =
            "dashboard-habit-loading";
        loading.textContent =
            dashboard_t("recovery.habitModal.loading");
        listBox.appendChild(loading);
        try {
            const [habitsPayload, userHabitsPayload] = await Promise.all([
                RecoveryAPI.getHabitsList(),
                RecoveryAPI.getUserHabits(userId)
            ]);
            const habits = normalizeHabits(habitsPayload);
            const userHabits = normalizeUserHabits(userHabitsPayload);
            const userHabitIds = new Set(userHabits
                .map(getHabitId)
                .filter(id => id > 0));
            const available = sortAvailable(habits.filter(habit => !userHabitIds.has(Number(habit.id))), currentSort);
            const added = sortAdded(habits.filter(habit => userHabitIds.has(Number(habit.id))));
            listBox.innerHTML = "";
            const availableHeader = document.createElement("div");
            availableHeader.className =
                "dashboard-habit-section-title";
            availableHeader.textContent =
                dashboard_t("recovery.habitModal.available");
            listBox.appendChild(availableHeader);
            if (available.length === 0) {
                const empty = document.createElement("div");
                empty.className =
                    "dashboard-habit-empty";
                empty.textContent =
                    dashboard_t("recovery.habitModal.emptyAvailable");
                listBox.appendChild(empty);
            }
            else {
                available.forEach(habit => {
                    listBox.appendChild(createHabitRow(habit, false, new Set()));
                });
            }
            const addedHeader = document.createElement("div");
            addedHeader.className =
                "dashboard-habit-section-title";
            addedHeader.textContent =
                dashboard_t("recovery.habitModal.alreadyAdded");
            listBox.appendChild(addedHeader);
            if (added.length === 0) {
                const empty = document.createElement("div");
                empty.className =
                    "dashboard-habit-empty dashboard-habit-empty-secondary";
                empty.textContent =
                    dashboard_t("recovery.habitModal.emptyAdded");
                listBox.appendChild(empty);
            }
            else {
                added.forEach(habit => {
                    listBox.appendChild(createHabitRow(habit, true, new Set()));
                });
            }
            updateSaveState();
        }
        catch (error) {
            console.error("Failed to load recovery habits:", error);
            listBox.innerHTML = "";
            const errorBox = document.createElement("div");
            errorBox.className =
                "dashboard-habit-error";
            errorBox.textContent =
                dashboard_t("recovery.habitModal.loadFailed");
            listBox.appendChild(errorBox);
            updateSaveState();
        }
    }
    function open() {
        backdrop.hidden = false;
        requestAnimationFrame(() => {
            backdrop.classList.add("open");
        });
        saveButton.disabled = true;
        void renderList();
    }
    function close() {
        backdrop.classList.remove("open");
        window.setTimeout(() => {
            if (!backdrop.classList.contains("open")) {
                backdrop.hidden = true;
            }
        }, 180);
        listBox.innerHTML = "";
        saveButton.disabled = true;
    }
    async function save() {
        const selected = Array.from(listBox.querySelectorAll(".dashboard-habit-row.dashboard-habit-selected"));
        if (selected.length === 0) {
            return;
        }
        saveButton.disabled = true;
        try {
            const habitIds = selected
                .map(row => Number(row.dataset.habitId))
                .filter(id => Number.isFinite(id) &&
                id > 0);
            if (habitIds.length === 0) {
                throw new Error("No valid habit IDs selected");
            }
            await Promise.all(habitIds.map(habitId => RecoveryAPI.addHabit(userId, habitId)));
            await refreshRecoveryWidget();
            window.dispatchEvent(new CustomEvent("dashboard:refresh"));
            close();
        }
        catch (error) {
            console.error("Failed to save recovery habits:", error);
            alert(dashboard_t("recovery.habitModal.saveFailed"));
            saveButton.disabled =
                false;
        }
    }
    openButton.addEventListener("click", open);
    backButton.addEventListener("click", close);
    saveButton.addEventListener("click", () => {
        void save();
    });
    backdrop.addEventListener("click", event => {
        if (event.target ===
            backdrop) {
            close();
        }
    });
    /*
     * Keep the original event delegation:
     * selecting a habit must work when clicking
     * anywhere inside the row.
     */
    listBox.addEventListener("click", event => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        const row = target.closest(".dashboard-habit-row");
        if (!row) {
            return;
        }
        /*
         * Already added habits are displayed
         * but cannot be selected again.
         */
        if (row.classList.contains("dashboard-habit-added")) {
            return;
        }
        row.classList.toggle("dashboard-habit-selected");
        /*
         * Keep the visual checked state
         * synchronized with the selected state.
         */
        const check = row.querySelector(".dashboard-habit-check");
        if (check) {
            const checked = row.classList.contains("dashboard-habit-selected");
            check.classList.toggle("dashboard-habit-checked", checked);
            check.textContent =
                checked
                    ? "✓"
                    : "";
        }
        updateSaveState();
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" &&
            !backdrop.hidden) {
            close();
        }
    });
    sortButtons.forEach(button => {
        button.addEventListener("click", () => {
            sortButtons.forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            currentSort =
                button.dataset.sort ||
                    "points";
            void renderList();
        });
    });
}
