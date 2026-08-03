import { RECOVERY_MESSAGES } from "./messages.js";
import { clearElement, createEmpty } from "./dom.js";
import { RecoveryAPI } from "./api.js";
import { refreshRecoveryDashboard } from "./dashboard.js";
import { showRecoveryToast } from "./toast.js";
import { ICONS } from "../icons/icons.js";

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

    snapshot.habits.forEach(habit => {
        const item = document.createElement("div");
        item.className = "habit-item";
        if (habit.completed) item.classList.add("habit-completed");

        const title = document.createElement("div");
        title.className = "habit-title";
        title.textContent = habit.name;

        const category = document.createElement("div");
        category.className = "habit-category";
        category.textContent = habit.category;

        const check = document.createElement("div");
        check.className = "habit-check";
        if (habit.completed) check.classList.add("habit-check-completed");

        check.addEventListener("click", async () => {
            check.classList.toggle("habit-check-completed");
            item.classList.toggle("habit-completed");

            try {
                await RecoveryAPI.logHabit(habit.user_habit_id);
            } catch {
                showRecoveryToast("Помилка при збереженні звички");
                return;
            }

            showRecoveryToast("Звичку виконано");
            await refreshRecoveryDashboard();
        });

        const removeBtn = document.createElement("button");
        removeBtn.className = "habit-btn-remove";
        removeBtn.innerHTML = ICONS.delete;

        let confirm = false;
        let timeoutId = null;

        removeBtn.addEventListener("click", async () => {
            if (!confirm) {
                confirm = true;
                removeBtn.classList.add("habit-remove-confirm");

                timeoutId = setTimeout(() => {
                    confirm = false;
                    removeBtn.classList.remove("habit-remove-confirm");
                }, 2000);

                return;
            }

            clearTimeout(timeoutId);

            await RecoveryAPI.removeHabit(habit.user_habit_id);
            await refreshRecoveryDashboard();
            showRecoveryToast("Звичку видалено");
        });

        item.appendChild(title);
        item.appendChild(category);
        item.appendChild(check);
        item.appendChild(removeBtn);

        el.appendChild(item);
    });
}
