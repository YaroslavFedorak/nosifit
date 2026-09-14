import { ICONS } from "../../../icons/index.js";
import { RecoveryAPI } from "./api.js";
import { refreshRecoveryWidget } from "../../widgets/recovery/index.js";
const CATEGORY_MAP = {
    hydration: "Вода",
    sleep: "Сон",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};
let initialized = false;
let currentSort = "points";
function normalizeHabits(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (payload &&
        typeof payload === "object") {
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
    if (payload &&
        typeof payload === "object") {
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
    if (iconKey &&
        iconKey in ICONS) {
        return ICONS[iconKey];
    }
    return ICONS.rest;
}
function localizeCategory(category) {
    if (!category) {
        return "";
    }
    return (CATEGORY_MAP[category] ||
        category);
}
function sortAvailable(habits, sortKey) {
    const sorted = [...habits];
    if (sortKey === "points") {
        return sorted.sort((a, b) => Number(b.points || 0) -
            Number(a.points || 0));
    }
    if (sortKey === "category") {
        return sorted.sort((a, b) => localizeCategory(a.category).localeCompare(localizeCategory(b.category), "uk"));
    }
    if (sortKey === "name") {
        return sorted.sort((a, b) => a.name.localeCompare(b.name, "uk"));
    }
    return sorted;
}
function sortAdded(habits) {
    return [...habits].sort((a, b) => a.name.localeCompare(b.name, "uk"));
}
function createHabitRow(habit, added) {
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
        habit.name;
    info.appendChild(title);
    if (habit.description) {
        const description = document.createElement("div");
        description.className =
            "dashboard-habit-description";
        description.textContent =
            habit.description;
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
        `Recovery +${Number(habit.points || 0)}`;
    const meta = document.createElement("div");
    meta.className =
        "dashboard-habit-meta";
    meta.textContent =
        localizeCategory(category);
    const check = document.createElement("div");
    check.className =
        "dashboard-habit-check";
    if (added) {
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
    const backdropElement = document.getElementById("habit-modal-backdrop");
    const openButtonElement = document.getElementById("dashboard-open-recovery");
    const backButtonElement = document.getElementById("habit-back-btn");
    const saveButtonElement = document.getElementById("save-habit");
    const listBoxElement = document.getElementById("habit-modal-list");
    if (!(backdropElement instanceof HTMLElement) ||
        !(backButtonElement instanceof HTMLButtonElement) ||
        !(saveButtonElement instanceof HTMLButtonElement) ||
        !(listBoxElement instanceof HTMLElement)) {
        console.error("Recovery habit modal elements not found");
        return;
    }
    const backdrop = backdropElement;
    const backButton = backButtonElement;
    const saveButton = saveButtonElement;
    const listBox = listBoxElement;
    const openButton = openButtonElement instanceof HTMLElement
        ? openButtonElement
        : null;
    const sortButtons = document.querySelectorAll(".dashboard-habit-sort-btn");
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
            "Завантаження звичок…";
        listBox.appendChild(loading);
        try {
            const [allHabitsPayload, userHabitsPayload] = await Promise.all([
                RecoveryAPI.getHabitsList(),
                RecoveryAPI.getUserHabits(userId)
            ]);
            const allHabits = normalizeHabits(allHabitsPayload);
            const userHabits = normalizeUserHabits(userHabitsPayload);
            const userHabitIds = new Set(userHabits
                .map(getHabitId)
                .filter(id => id > 0));
            const available = allHabits.filter(habit => !userHabitIds.has(Number(habit.id)));
            const added = allHabits.filter(habit => userHabitIds.has(Number(habit.id)));
            const sortedAvailable = sortAvailable(available, currentSort);
            const sortedAdded = sortAdded(added);
            listBox.innerHTML = "";
            const availableHeader = document.createElement("div");
            availableHeader.className =
                "dashboard-habit-section-title";
            availableHeader.textContent =
                "Доступні звички";
            listBox.appendChild(availableHeader);
            if (sortedAvailable.length === 0) {
                const empty = document.createElement("div");
                empty.className =
                    "dashboard-habit-empty";
                empty.textContent =
                    "Усі доступні звички вже додані";
                listBox.appendChild(empty);
            }
            else {
                sortedAvailable.forEach(habit => {
                    listBox.appendChild(createHabitRow(habit, false));
                });
            }
            const addedHeader = document.createElement("div");
            addedHeader.className =
                "dashboard-habit-section-title";
            addedHeader.textContent =
                "Вже додані";
            listBox.appendChild(addedHeader);
            if (sortedAdded.length === 0) {
                const empty = document.createElement("div");
                empty.className =
                    "dashboard-habit-empty dashboard-habit-empty-secondary";
                empty.textContent =
                    "Ще немає доданих звичок";
                listBox.appendChild(empty);
            }
            else {
                sortedAdded.forEach(habit => {
                    listBox.appendChild(createHabitRow(habit, true));
                });
            }
            updateSaveState();
        }
        catch (error) {
            console.error("Failed to load recovery habits", error);
            listBox.innerHTML = "";
            const errorBox = document.createElement("div");
            errorBox.className =
                "dashboard-habit-error";
            errorBox.textContent =
                "Не вдалося завантажити звички";
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
                .filter(id => id > 0);
            await Promise.all(habitIds.map(habitId => RecoveryAPI.addHabit(userId, habitId)));
            await refreshRecoveryWidget();
            close();
        }
        catch (error) {
            console.error("Failed to save recovery habits", error);
            alert("Не вдалося зберегти звички");
            saveButton.disabled = false;
        }
    }
    if (openButton) {
        openButton.addEventListener("click", open);
    }
    backButton.addEventListener("click", close);
    saveButton.addEventListener("click", () => {
        void save();
    });
    backdrop.addEventListener("click", event => {
        if (event.target === backdrop) {
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
    listBox.addEventListener("click", event => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        const row = target.closest(".dashboard-habit-row");
        if (!row) {
            return;
        }
        if (row.classList.contains("dashboard-habit-added")) {
            return;
        }
        row.classList.toggle("dashboard-habit-selected");
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
}
