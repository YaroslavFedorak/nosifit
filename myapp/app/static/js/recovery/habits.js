import { RECOVERY_MESSAGES } from "./messages.js";
import { clearElement, createCard, createTitle, createEmpty } from "./dom.js";
import { RecoveryAPI } from "./api.js";
import { refreshRecoveryDashboard } from "./dashboard.js";
import { showRecoveryToast } from "./toast.js";

export function renderHabitsWidget(snapshot, options = {}) {
    const el = document.getElementById("habits-widget");
    if (!el) return;

    clearElement(el);

    if (options.loading) {
        el.textContent = RECOVERY_MESSAGES.loading;
        return;
    }

    if (options.error) {
        el.textContent = RECOVERY_MESSAGES.error;
        return;
    }

    if (!snapshot || !snapshot.habits || snapshot.habits.length === 0) {
        el.appendChild(createEmpty(RECOVERY_MESSAGES.habits.empty));
        return;
    }

    const card = createCard("habits-card");
    card.appendChild(createTitle(RECOVERY_MESSAGES.habits.title));

    const list = document.createElement("div");
    list.className = "habits-content";

    snapshot.habits.forEach(habit => {
        const item = document.createElement("div");
        item.className = "habit-item";
        if (habit.completed) item.classList.add("habit-completed");

        const left = document.createElement("div");
        left.className = "habit-left";

        const icon = document.createElement("div");
        icon.className = "habit-check";
        if (habit.completed) icon.classList.add("habit-check-completed");

        const title = document.createElement("div");
        title.className = "habit-title";
        title.textContent = habit.name;

        const meta = document.createElement("div");
        meta.className = "habit-meta";
        meta.textContent = habit.category;

        left.appendChild(icon);
        left.appendChild(title);
        left.appendChild(meta);

        const actions = document.createElement("div");
        actions.className = "habit-actions";

        const completeBtn = document.createElement("button");
        completeBtn.className = "habit-btn";
        completeBtn.textContent = habit.completed ? "✓" : "Виконати";

        completeBtn.addEventListener("click", async () => {
            try {
                await RecoveryAPI.logHabit(habit.user_habit_id);
                showRecoveryToast("Звичку виконано!");
                await refreshRecoveryDashboard();
            } catch (e) {
                showRecoveryToast("Помилка при збереженні звички");
            }
        });

        const removeBtn = document.createElement("button");
        removeBtn.className = "habit-btn-remove";
        removeBtn.textContent = "✕";

        removeBtn.addEventListener("click", async () => {
            await RecoveryAPI.removeHabit(habit.user_habit_id);
            await refreshRecoveryDashboard();
            showRecoveryToast("Звичку видалено");
        });

        actions.appendChild(completeBtn);
        actions.appendChild(removeBtn);

        item.appendChild(left);
        item.appendChild(actions);

        list.appendChild(item);
    });

    card.appendChild(list);
    el.appendChild(card);
}
