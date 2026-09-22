import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";
import { ICONS } from "../../icons/index.js";
const CATEGORY_LABELS = {
    sleep: "Сон",
    hydration: "Вода",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};
const CATEGORY_COLORS = {
    sleep: "#8b95b8",
    hydration: "#5b9db0",
    nutrition: "#b9a06d",
    activity: "#6fae87",
    recovery: "#9a7bb5",
    stress: "#b67c6b",
    massage: "#b58a9f"
};
const CATEGORY_BACKGROUNDS = {
    sleep: "rgba(139, 149, 184, 0.10)",
    hydration: "rgba(91, 157, 176, 0.10)",
    nutrition: "rgba(185, 160, 109, 0.10)",
    activity: "rgba(111, 174, 135, 0.10)",
    recovery: "rgba(154, 123, 181, 0.10)",
    stress: "rgba(182, 124, 107, 0.10)",
    massage: "rgba(181, 138, 159, 0.10)"
};
const CATEGORY_ICONS = {
    sleep: "bed",
    hydration: "droplet",
    nutrition: "meal",
    activity: "walk",
    recovery: "rest",
    stress: "breathing",
    massage: "massage"
};
const ICON_ALIASES = {
    sleep: "bed",
    water: "droplet",
    hydration: "droplet",
    nutrition: "meal",
    activity: "walk",
    recovery: "rest",
    stress: "breathing",
    massage: "massage"
};
let selectedHabitId = null;
let habits = [];
let addedHabits = [];
let sortMode = "points";
let currentUserId = null;
let initialized = false;
function getElements() {
    const backdrop = document.getElementById("habit-modal-backdrop");
    const list = document.getElementById("habit-modal-list");
    const openButton = document.getElementById("open-habit-modal");
    const backButton = document.getElementById("habit-back-btn");
    const saveButton = document.getElementById("save-habit");
    const sortButtons = document.querySelectorAll(".habit-sort-btn");
    if (!backdrop ||
        !list ||
        !openButton ||
        !backButton ||
        !saveButton) {
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
function getHabitId(habit) {
    return (habit.id ??
        habit.habit_id ??
        habit.user_habit_id ??
        null);
}
function getUserHabitId(habit) {
    return (habit.habit_id ??
        habit.id ??
        habit.user_habit_id ??
        null);
}
function getHabitName(habit) {
    return habit.name || "Звичка";
}
function getHabitPoints(habit) {
    return habit.points ?? 0;
}
function getCategoryKey(category) {
    return category || "recovery";
}
function getCategoryLabel(category) {
    const key = getCategoryKey(category);
    return (CATEGORY_LABELS[key] ??
        category ??
        "Відновлення");
}
function getCategoryColor(category) {
    return (CATEGORY_COLORS[getCategoryKey(category)] ??
        CATEGORY_COLORS.recovery);
}
function getCategoryBackground(category) {
    return (CATEGORY_BACKGROUNDS[getCategoryKey(category)] ??
        CATEGORY_BACKGROUNDS.recovery);
}
function getHabitIcon(habit) {
    const category = getCategoryKey(habit.category);
    const requestedIcon = habit.icon?.trim() || "";
    let iconName = CATEGORY_ICONS[category] ||
        "rest";
    if (requestedIcon) {
        iconName =
            ICON_ALIASES[requestedIcon] ||
                requestedIcon;
    }
    return (ICONS[iconName] ??
        ICONS.rest);
}
function normalizeHabits(data) {
    if (Array.isArray(data)) {
        return data;
    }
    if (data &&
        typeof data === "object") {
        const value = data;
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
function normalizeUserHabits(data) {
    if (Array.isArray(data)) {
        return data;
    }
    if (data &&
        typeof data === "object") {
        const value = data;
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
function sortHabits(source) {
    const result = [...source];
    if (sortMode === "name") {
        return result.sort((a, b) => getHabitName(a).localeCompare(getHabitName(b), "uk"));
    }
    if (sortMode === "category") {
        return result.sort((a, b) => getCategoryLabel(a.category).localeCompare(getCategoryLabel(b.category), "uk"));
    }
    return result.sort((a, b) => getHabitPoints(b) -
        getHabitPoints(a));
}
function sortAddedHabits(source) {
    return [...source].sort((a, b) => getHabitName(a).localeCompare(getHabitName(b), "uk"));
}
function createSectionTitle(text) {
    const title = document.createElement("div");
    title.className =
        "habit-modal-section-title";
    title.textContent = text;
    return title;
}
function createEmptyState(text, secondary = false) {
    const empty = document.createElement("div");
    empty.className =
        "habit-modal-empty";
    if (secondary) {
        empty.classList.add("habit-modal-empty-secondary");
    }
    empty.textContent = text;
    return empty;
}
function createHabitItem(habit, elements, added = false) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "habit-row";
    if (added) {
        item.classList.add("habit-row-added");
    }
    const habitId = getHabitId(habit);
    const isSelected = habitId !== null &&
        String(habitId) ===
            String(selectedHabitId);
    if (isSelected) {
        item.classList.add("selected");
    }
    const categoryColor = getCategoryColor(habit.category);
    const categoryBackground = getCategoryBackground(habit.category);
    item.style.setProperty("--cat-color", categoryColor);
    item.style.setProperty("--cat-color-bg", categoryBackground);
    const left = document.createElement("span");
    left.className =
        "habit-left";
    const icon = document.createElement("span");
    icon.className =
        "habit-modal-icon";
    icon.innerHTML =
        getHabitIcon(habit);
    const info = document.createElement("span");
    info.className =
        "habit-info";
    const title = document.createElement("span");
    title.className =
        "habit-title";
    title.textContent =
        getHabitName(habit);
    const description = document.createElement("span");
    description.className =
        "habit-description";
    description.textContent =
        habit.description ||
            getCategoryLabel(habit.category);
    info.appendChild(title);
    info.appendChild(description);
    left.appendChild(icon);
    left.appendChild(info);
    const right = document.createElement("span");
    right.className =
        "habit-right";
    const points = document.createElement("span");
    points.className =
        "habit-points";
    points.textContent =
        `Recovery +${getHabitPoints(habit)}`;
    const meta = document.createElement("span");
    meta.className =
        "habit-meta";
    meta.textContent =
        getCategoryLabel(habit.category);
    const check = document.createElement("span");
    check.className =
        "habit-check";
    if (added ||
        isSelected) {
        check.classList.add("checked");
        check.textContent =
            "✓";
    }
    right.appendChild(points);
    right.appendChild(meta);
    right.appendChild(check);
    item.appendChild(left);
    item.appendChild(right);
    if (!added) {
        item.addEventListener("click", () => {
            const currentlySelected = habitId !== null &&
                String(habitId) ===
                    String(selectedHabitId);
            if (currentlySelected) {
                selectedHabitId =
                    null;
            }
            else {
                selectedHabitId =
                    habitId;
            }
            elements.saveButton.disabled =
                selectedHabitId ===
                    null;
            renderFullList(elements, habits, addedHabits);
        });
    }
    return item;
}
function renderFullList(elements, available, added) {
    elements.list.innerHTML = "";
    const sortedAvailable = sortHabits(available);
    const sortedAdded = sortAddedHabits(added);
    elements.list.appendChild(createSectionTitle("Доступні звички"));
    if (sortedAvailable.length ===
        0) {
        elements.list.appendChild(createEmptyState("Усі доступні звички вже додані"));
    }
    else {
        sortedAvailable.forEach(habit => {
            elements.list.appendChild(createHabitItem(habit, elements));
        });
    }
    elements.list.appendChild(createSectionTitle("Вже додані"));
    if (sortedAdded.length ===
        0) {
        elements.list.appendChild(createEmptyState("Ще немає доданих звичок", true));
    }
    else {
        sortedAdded.forEach(habit => {
            elements.list.appendChild(createHabitItem(habit, elements, true));
        });
    }
}
function openModal(elements) {
    selectedHabitId = null;
    elements.saveButton.disabled =
        true;
    elements.backdrop.hidden =
        false;
    requestAnimationFrame(() => {
        elements.backdrop.classList.add("open");
    });
    document.body.classList.add("modal-open");
    void loadHabits(elements);
}
function closeModal(elements) {
    elements.backdrop.classList.remove("open");
    window.setTimeout(() => {
        if (!elements.backdrop.classList.contains("open")) {
            elements.backdrop.hidden =
                true;
        }
    }, 180);
    document.body.classList.remove("modal-open");
    selectedHabitId = null;
    elements.saveButton.disabled =
        true;
}
async function loadHabits(elements) {
    elements.list.innerHTML = "";
    const loading = document.createElement("div");
    loading.className =
        "habit-modal-loading";
    loading.textContent =
        "Завантаження...";
    elements.list.appendChild(loading);
    if (currentUserId === null) {
        return;
    }
    try {
        const [allHabitsPayload, userHabitsPayload] = await Promise.all([
            RecoveryAPI.getHabitsList(),
            RecoveryAPI.getUserHabits(currentUserId)
        ]);
        const allHabits = normalizeHabits(allHabitsPayload);
        const userHabits = normalizeUserHabits(userHabitsPayload);
        const userHabitIds = new Set(userHabits
            .map(getUserHabitId)
            .filter(id => id !== null)
            .map(id => String(id)));
        const available = allHabits.filter(habit => {
            const habitId = getHabitId(habit);
            return (habitId !== null &&
                !userHabitIds.has(String(habitId)));
        });
        const added = allHabits.filter(habit => {
            const habitId = getHabitId(habit);
            return (habitId !== null &&
                userHabitIds.has(String(habitId)));
        });
        habits = available;
        addedHabits = added;
        renderFullList(elements, habits, addedHabits);
    }
    catch {
        elements.list.innerHTML = "";
        const error = document.createElement("div");
        error.className =
            "habit-modal-error";
        error.textContent =
            "Не вдалося завантажити звички";
        elements.list.appendChild(error);
    }
}
async function saveHabit(elements) {
    if (currentUserId === null ||
        selectedHabitId === null) {
        return;
    }
    elements.saveButton.disabled =
        true;
    try {
        await RecoveryAPI.addHabit(currentUserId, selectedHabitId);
        closeModal(elements);
        await refreshRecoveryDashboard(currentUserId);
    }
    catch {
        elements.saveButton.disabled =
            false;
    }
}
function setSortMode(mode, elements) {
    sortMode = mode;
    elements.sortButtons.forEach(button => {
        button.classList.toggle("active", button.dataset.sort ===
            mode);
    });
    renderFullList(elements, habits, addedHabits);
}
export function initHabitModal(userId) {
    if (initialized) {
        return;
    }
    const elements = getElements();
    if (!elements) {
        return;
    }
    initialized = true;
    currentUserId = userId;
    elements.openButton.addEventListener("click", () => {
        openModal(elements);
    });
    elements.backButton.addEventListener("click", () => {
        closeModal(elements);
    });
    elements.saveButton.addEventListener("click", () => {
        void saveHabit(elements);
    });
    elements.sortButtons.forEach(button => {
        button.addEventListener("click", () => {
            const mode = button.dataset.sort;
            if (mode === "points" ||
                mode === "category" ||
                mode === "name") {
                setSortMode(mode, elements);
            }
        });
    });
    elements.backdrop.addEventListener("click", event => {
        if (event.target ===
            elements.backdrop) {
            closeModal(elements);
        }
    });
}
