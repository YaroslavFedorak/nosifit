import { RECOVERY_MESSAGES } from "./messages.js";
import { clearElement, createEmpty } from "./dom.js";
import { RecoveryAPI } from "./api.js";
import { refreshRecoveryDashboard } from "./dashboard.js";
import { showRecoveryToast } from "./toast.js";
import { ICONS } from "../icons/index.js";

const CATEGORY_LABELS = {
    sleep: "Сон",
    hydration: "Вода",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};

function label(category) {
    return CATEGORY_LABELS[category] || category;
}

function buildReason(habit) {
    switch (habit.category) {
        case "sleep": return "Рекомендовано через якість сну";
        case "hydration": return "Рекомендовано через рівень гідратації";
        case "nutrition": return "Рекомендовано для підтримки харчування";
        case "activity": return "Рекомендовано після навантаження";
        case "recovery": return "Рекомендовано для покращення відновлення";
        case "stress": return "Рекомендовано через рівень стресу";
        case "massage": return "Рекомендовано для розслаблення м'язів";
        default: return "Рекомендовано для балансу відновлення";
    }
}

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
        const categoryClass = `habit-cat-${habit.category}`;
        item.className = `habit-item ${categoryClass}`;
        if (habit.completed) item.classList.add("habit-completed");

        const main = document.createElement("div");
        main.className = "habit-main";

        const iconBox = document.createElement("div");
        iconBox.className = "habit-icon";
        const iconKey = habit.icon || "rest";
        iconBox.innerHTML = ICONS[iconKey] || ICONS.rest;

        const textBox = document.createElement("div");
        textBox.className = "habit-text";

        const title = document.createElement("div");
        title.className = "habit-title";
        title.textContent = habit.name;

        const metaRow = document.createElement("div");
        metaRow.className = "habit-meta-row";

        const category = document.createElement("div");
        category.className = "habit-category-badge";
        category.textContent = label(habit.category);

        const reason = document.createElement("div");
        reason.className = "habit-reason";
        reason.textContent = buildReason(habit);

        metaRow.appendChild(category);

        textBox.appendChild(title);
        textBox.appendChild(metaRow);
        textBox.appendChild(reason);

        main.appendChild(iconBox);
        main.appendChild(textBox);

        const actions = document.createElement("div");
        actions.className = "habit-actions";

        const impact = document.createElement("div");
        impact.className = "habit-recovery-impact";
        impact.textContent = `Recovery +${habit.points}`;

        const check = document.createElement("button");
        check.type = "button";
        check.className = "habit-check";
        if (habit.completed) check.classList.add("habit-check-completed");

        check.addEventListener("click", async () => {
            check.classList.toggle("habit-check-completed");
            item.classList.toggle("habit-completed");
            item.classList.add("habit-animate");
            setTimeout(() => item.classList.remove("habit-animate"), 160);

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
        removeBtn.type = "button";
        removeBtn.className = "habit-btn-remove";
        removeBtn.innerHTML = ICONS.delete;

        let confirm = false;
        let timeoutId = null;

        removeBtn.addEventListener("click", async () => {
            if (!confirm) {
                confirm = true;
                removeBtn.classList.add("habit-remove-pending");
                timeoutId = setTimeout(() => {
                    confirm = false;
                    removeBtn.classList.remove("habit-remove-pending");
                }, 2000);
                return;
            }

            clearTimeout(timeoutId);

            try {
                await RecoveryAPI.removeHabit(habit.user_habit_id);
                await refreshRecoveryDashboard();
                showRecoveryToast("Звичку видалено");
            } catch {
                showRecoveryToast("Помилка при видаленні звички");
            } finally {
                confirm = false;
                removeBtn.classList.remove("habit-remove-pending");
            }
        });

        actions.appendChild(impact);
        actions.appendChild(check);
        actions.appendChild(removeBtn);

        item.appendChild(main);
        item.appendChild(actions);

        el.appendChild(item);
    });
}
