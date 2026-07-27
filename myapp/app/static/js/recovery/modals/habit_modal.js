import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";

let habitsCache = null;
let initialized = false;
let currentSort = "points";

async function loadHabits() {
    if (habitsCache !== null) {
        return habitsCache;
    }

    try {
        const habits = await RecoveryAPI.getHabitsList();
        habitsCache = Array.isArray(habits) ? habits : [];
    } catch {
        habitsCache = [];
    }

    return habitsCache;
}

function sortHabits(habits, sortKey) {
    if (sortKey === "points") {
        return habits.sort((a, b) => b.points - a.points);
    }
    if (sortKey === "category") {
        return habits.sort((a, b) => a.category.localeCompare(b.category));
    }
    if (sortKey === "name") {
        return habits.sort((a, b) => a.name.localeCompare(b.name));
    }
    return habits;
}

function toggleHabit(row) {
    row.classList.toggle("selected");
}

export function initHabitModal(userId) {
    if (initialized) {
        return;
    }
    initialized = true;

    const backdrop = document.getElementById("habit-modal-backdrop");
    const openBtn = document.getElementById("open-habit-modal");
    const closeBtn = document.getElementById("close-habit-modal");
    const saveBtn = document.getElementById("save-habit");
    const backBtn = document.getElementById("habit-back-btn");
    const listBox = document.getElementById("habit-modal-list");
    const sortButtons = document.querySelectorAll(".habit-sort-btn");

    if (!backdrop || !openBtn || !closeBtn || !saveBtn || !listBox) return;

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    saveBtn.addEventListener("click", save);
    if (backBtn) backBtn.addEventListener("click", close);

    listBox.addEventListener("click", (event) => {
        const row = event.target.closest(".habit-modal-item");
        if (!row) return;
        toggleHabit(row);
    });

    sortButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            sortButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentSort = btn.dataset.sort;
            renderList();
        });
    });

    async function renderList() {
        const habits = await loadHabits();
        const sorted = sortHabits([...habits], currentSort);

        listBox.innerHTML = "";

        sorted.forEach(habit => {
            const row = document.createElement("div");
            row.className = "habit-modal-item";
            row.dataset.habitId = habit.id;

            const title = document.createElement("div");
            title.className = "habit-title";
            title.textContent = `${habit.name} (+${habit.points})`;

            const meta = document.createElement("div");
            meta.className = "habit-meta";
            meta.textContent = habit.category;

            row.appendChild(title);
            row.appendChild(meta);

            listBox.appendChild(row);
        });
    }

    async function open() {
        backdrop.classList.add("open");
        renderList();
    }

    function close() {
        backdrop.classList.remove("open");
        listBox.innerHTML = "";
    }

    async function save() {
        const selected = [...listBox.querySelectorAll(".habit-modal-item.selected")];
        if (selected.length === 0) {
            alert("Оберіть хоча б одну звичку");
            return;
        }

        saveBtn.disabled = true;

        try {
            for (const row of selected) {
                const habitId = Number(row.dataset.habitId);
                if (!Number.isNaN(habitId)) {
                    await RecoveryAPI.addHabit(userId, habitId);
                }
            }

            await RecoveryAPI.generateSnapshot(userId);
            await refreshRecoveryDashboard(userId);

            close();
        } finally {
            saveBtn.disabled = false;
        }
    }
}
