import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";
import { ICONS } from "../../icons/index.js";
import { showRecoveryToast } from "../toast.js";

let initialized = false;
let currentSort = "points";

const CATEGORY_MAP = {
    hydration: "Вода",
    sleep: "Сон",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес"
};

function localizeCategory(category) {
    return CATEGORY_MAP[category] || category || "";
}

async function loadAllHabits() {
    const habits = await RecoveryAPI.getHabitsList();
    return Array.isArray(habits) ? habits : [];
}

async function loadUserHabits(userId) {
    const userHabits = await RecoveryAPI.getUserHabits(userId);
    return Array.isArray(userHabits) ? userHabits : [];
}

function sortAvailable(habits, sortKey) {
    const sorted = [...habits];
    if (sortKey === "points") return sorted.sort((a, b) => b.points - a.points);
    if (sortKey === "category") return sorted.sort((a, b) => a.category.localeCompare(b.category));
    if (sortKey === "name") return sorted.sort((a, b) => a.name.localeCompare(b.name));
    return sorted;
}

function sortAdded(habits) {
    return [...habits].sort((a, b) => a.name.localeCompare(b.name));
}

function createHabitRow(habit, added) {
    const row = document.createElement("div");
    row.className = "habit-row";
    if (added) row.classList.add("habit-added");

    const left = document.createElement("div");
    left.className = "habit-left";

    const icon = document.createElement("div");
    icon.className = "habit-modal-icon";

    const iconKey = habit.icon || "rest";
    icon.innerHTML = ICONS[iconKey] || ICONS.rest;

    const info = document.createElement("div");
    info.className = "habit-info";

    const title = document.createElement("div");
    title.className = "habit-title";
    title.textContent = habit.name;

    const description = document.createElement("div");
    description.className = "habit-description";
    description.textContent = habit.description || "";

    const meta = document.createElement("div");
    meta.className = "habit-meta";
    meta.textContent = localizeCategory(habit.category);

    info.appendChild(title);
    if (habit.description) info.appendChild(description);
    if (habit.category) info.appendChild(meta);

    left.appendChild(icon);
    left.appendChild(info);

    const right = document.createElement("div");
    right.className = "habit-right";

    const points = document.createElement("div");
    points.className = "habit-points";
    points.textContent = `Recovery +${habit.points}`;

    right.appendChild(points);

    if (added) {
        const status = document.createElement("div");
        status.className = "habit-status";
        status.textContent = "Додано";
        right.appendChild(status);
    }

    const check = document.createElement("div");
    check.className = "habit-check";
    if (added) {
        check.classList.add("checked");
        check.textContent = "✓";
    }
    right.appendChild(check);

    row.appendChild(left);
    row.appendChild(right);

    row.dataset.habitId = habit.id;

    return row;
}

export function initHabitModal(userId) {
    const backdrop = document.getElementById("habit-modal-backdrop");
    const openBtn = document.getElementById("open-habit-modal");
    const closeBtn = document.getElementById("close-habit-modal");
    const backBtn = document.getElementById("habit-back-btn");
    const saveBtn = document.getElementById("save-habit");
    const listBox = document.getElementById("habit-modal-list");
    const sortButtons = document.querySelectorAll(".habit-sort-btn");

    if (initialized) return;

    if (!backdrop || !openBtn || !closeBtn || !backBtn || !saveBtn || !listBox) {
        return;
    }

    initialized = true;

    function updateSaveState() {
        const selected = listBox.querySelectorAll(".habit-row.selected");
        saveBtn.disabled = selected.length === 0;
    }

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    backBtn.addEventListener("click", close);
    saveBtn.addEventListener("click", save);

    sortButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            sortButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentSort = btn.dataset.sort;
            renderList();
        });
    });

    listBox.addEventListener("click", (event) => {
        const row = event.target.closest(".habit-row");
        if (!row) return;
        if (row.classList.contains("habit-added")) return;

        row.classList.toggle("selected");

        const check = row.querySelector(".habit-check");
        if (check) {
            const checked = row.classList.contains("selected");
            check.classList.toggle("checked", checked);
            check.textContent = checked ? "✓" : "";
        }

        updateSaveState();
    });

    async function renderList() {
        const allHabits = await loadAllHabits();
        const userHabits = await loadUserHabits(userId);
        const userHabitIds = new Set(userHabits.map(h => h.id));

        const available = allHabits.filter(h => !userHabitIds.has(h.id));
        const added = allHabits.filter(h => userHabitIds.has(h.id));

        const sortedAvailable = sortAvailable(available, currentSort);
        const sortedAdded = sortAdded(added);

        listBox.innerHTML = "";

        const availableHeader = document.createElement("div");
        availableHeader.className = "habit-section-title";
        availableHeader.textContent = "Доступні";
        listBox.appendChild(availableHeader);

        if (sortedAvailable.length === 0) {
            const empty = document.createElement("div");
            empty.className = "habit-empty";
            empty.textContent = "Усі доступні звички вже додані 🎉";
            listBox.appendChild(empty);
        } else {
            sortedAvailable.forEach(habit => {
                listBox.appendChild(createHabitRow(habit, false));
            });
        }

        const addedHeader = document.createElement("div");
        addedHeader.className = "habit-section-title";
        addedHeader.textContent = "Вже додані";
        listBox.appendChild(addedHeader);

        sortedAdded.forEach(habit => {
            listBox.appendChild(createHabitRow(habit, true));
        });

        updateSaveState();
    }

    async function open() {
        backdrop.classList.add("open");
        saveBtn.disabled = true;
        await renderList();
    }

    function close() {
        backdrop.classList.remove("open");
        listBox.innerHTML = "";
        saveBtn.disabled = true;
    }

    async function save() {
        const selected = [...listBox.querySelectorAll(".habit-row.selected")];
        if (selected.length === 0) return;

        saveBtn.disabled = true;

        try {
            const habitIds = selected.map(row => Number(row.dataset.habitId));
            const requests = habitIds.map(id => RecoveryAPI.addHabit(userId, id));

            await Promise.all(requests);
            await refreshRecoveryDashboard(userId);

            showRecoveryToast("Звички успішно додано");
            close();
        } catch (e) {
            showRecoveryToast("Помилка при збереженні звичок");
        } finally {
            saveBtn.disabled = false;
        }
    }
}
