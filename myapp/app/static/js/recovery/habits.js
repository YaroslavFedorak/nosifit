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
    return CATEGORY_LABELS[category] || category || "";
}

function buildReason(habit) {
    switch (habit.category) {
        case "sleep":
            return "Рекомендовано через якість сну";
        case "hydration":
            return "Рекомендовано через рівень гідратації";
        case "nutrition":
            return "Рекомендовано для підтримки харчування";
        case "activity":
            return "Рекомендовано після навантаження";
        case "recovery":
            return "Рекомендовано для покращення відновлення";
        case "stress":
            return "Рекомендовано через рівень стресу";
        case "massage":
            return "Рекомендовано для розслаблення м'язів";
        default:
            return "Рекомендовано для балансу відновлення";
    }
}

function createHabitItem(habit) {
    const item = document.createElement("div");
    item.className = `habit-item ${habit.completed ? "habit-completed" : ""} habit-user`;
    if (habit.category) item.classList.add(`habit-cat-${habit.category}`);

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
    title.textContent = habit.name || "";

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
    impact.textContent = habit.points != null ? `Recovery +${habit.points}` : "";

    const check = document.createElement("button");
    check.type = "button";
    check.className = "habit-check";
    check.dataset.userHabitId = habit.user_habit_id || "";
    if (habit.completed) check.classList.add("habit-check-completed");
    check.title = habit.completed ? "Відмінити" : "Позначити як виконано";

    check.addEventListener("click", async () => {
        const userHabitId = check.dataset.userHabitId;
        if (!userHabitId) {
            showRecoveryToast("Невідомий ідентифікатор звички");
            return;
        }

        check.disabled = true;
        const wasCompleted = check.classList.contains("habit-check-completed");
        check.classList.toggle("habit-check-completed");
        item.classList.toggle("habit-completed");
        item.classList.add("habit-animate");
        setTimeout(() => item.classList.remove("habit-animate"), 160);

        try {
            await RecoveryAPI.logHabit(userHabitId);
            showRecoveryToast(wasCompleted ? "Скасовано" : "Звичку виконано");
            await refreshRecoveryDashboard();
        } catch (err) {
            if (wasCompleted) {
                check.classList.remove("habit-check-completed");
                item.classList.remove("habit-completed");
            } else {
                check.classList.add("habit-check-completed");
                item.classList.add("habit-completed");
            }
            showRecoveryToast("Помилка при збереженні звички");
        } finally {
            check.disabled = false;
        }
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "habit-btn-remove";
    removeBtn.innerHTML = ICONS.delete;
    removeBtn.dataset.userHabitId = habit.user_habit_id || "";

    let confirm = false;
    let timeoutId = null;

    removeBtn.addEventListener("click", async () => {
        const userHabitId = removeBtn.dataset.userHabitId;
        if (!userHabitId) {
            showRecoveryToast("Невідомий ідентифікатор звички");
            return;
        }

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
        removeBtn.disabled = true;
        try {
            await RecoveryAPI.removeHabit(userHabitId);
            showRecoveryToast("Звичку видалено");
            await refreshRecoveryDashboard();
        } catch (err) {
            showRecoveryToast("Помилка при видаленні звички");
        } finally {
            confirm = false;
            removeBtn.classList.remove("habit-remove-pending");
            removeBtn.disabled = false;
        }
    });

    actions.appendChild(impact);
    actions.appendChild(check);
    actions.appendChild(removeBtn);

    item.appendChild(main);
    item.appendChild(actions);

    return item;
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

    if (!snapshot || !Array.isArray(snapshot.habits) || snapshot.habits.length === 0) {
        el.appendChild(createEmpty(RECOVERY_MESSAGES.habits.empty));
        return;
    }

    const userAdded = snapshot.habits.filter(h => h && (h.user_habit_id || h.user_habit_id === 0));
    if (!userAdded || userAdded.length === 0) {
        el.appendChild(createEmpty(RECOVERY_MESSAGES.habits.empty));
        return;
    }

    const previewCount = 8;
    const preview = userAdded.slice(0, previewCount);

    const grid = document.createElement("div");
    grid.className = "habits-grid two-col";

    const left = document.createElement("div");
    left.className = "habits-col";
    const right = document.createElement("div");
    right.className = "habits-col";

    preview.forEach((h, i) => {
        const col = i % 2 === 0 ? left : right;
        col.appendChild(createHabitItem(h));
    });

    grid.appendChild(left);
    grid.appendChild(right);
    el.appendChild(grid);

    if (userAdded.length > previewCount) {
        const footer = document.createElement("div");
        footer.className = "habits-widget-footer";
        const moreBtn = document.createElement("button");
        moreBtn.type = "button";
        moreBtn.className = "rc-btn rc-btn-sm";
        moreBtn.textContent = `Показати всі (${userAdded.length})`;
        moreBtn.addEventListener("click", () => {
            clearElement(el);
            const fullGrid = document.createElement("div");
            fullGrid.className = "habits-grid two-col";
            const l = document.createElement("div");
            l.className = "habits-col";
            const r = document.createElement("div");
            r.className = "habits-col";
            userAdded.forEach((h, idx) => {
                const col = idx % 2 === 0 ? l : r;
                col.appendChild(createHabitItem(h));
            });
            fullGrid.appendChild(l);
            fullGrid.appendChild(r);
            el.appendChild(fullGrid);
            const back = document.createElement("div");
            back.className = "habits-widget-footer";
            const backBtn = document.createElement("button");
            backBtn.type = "button";
            backBtn.className = "rc-btn rc-btn-sm";
            backBtn.textContent = "Показати менше";
            backBtn.addEventListener("click", () => renderHabitsWidget(snapshot));
            back.appendChild(backBtn);
            el.appendChild(back);
        });
        footer.appendChild(moreBtn);
        el.appendChild(footer);
    }
}
