const CATEGORY_LABELS = {
    sleep: "Сон",
    hydration: "Вода",
    nutrition: "Харчування",
    activity: "Активність",
    recovery: "Відновлення",
    stress: "Стрес",
    massage: "Масаж"
};
const CATEGORY_REASONS = {
    sleep: "Рекомендовано через якість сну",
    hydration: "Рекомендовано через рівень гідратації",
    nutrition: "Рекомендовано для підтримки харчування",
    activity: "Рекомендовано після навантаження",
    recovery: "Рекомендовано для покращення відновлення",
    stress: "Рекомендовано через рівень стресу",
    massage: "Рекомендовано для розслаблення м'язів"
};
function getElement(id) {
    return document.getElementById(id);
}
function getCategoryLabel(category) {
    if (!category) {
        return "";
    }
    return CATEGORY_LABELS[category] || category;
}
function getReason(category) {
    if (!category) {
        return "Рекомендовано для балансу відновлення";
    }
    return (CATEGORY_REASONS[category] ||
        "Рекомендовано для балансу відновлення");
}
function getIcon(habit) {
    const icons = window;
    const iconKey = habit.icon || "rest";
    return icons.ICONS?.[iconKey] || "";
}
function createHabitItem(habit) {
    const item = document.createElement("div");
    item.className = "habit-item";
    if (habit.completed) {
        item.classList.add("habit-completed");
    }
    if (habit.category) {
        item.classList.add(`habit-cat-${habit.category}`);
    }
    const main = document.createElement("div");
    main.className = "habit-main";
    const icon = document.createElement("div");
    icon.className = "habit-icon";
    icon.innerHTML = getIcon(habit);
    const text = document.createElement("div");
    text.className = "habit-text";
    const title = document.createElement("div");
    title.className = "habit-title";
    title.textContent = habit.name || "";
    const meta = document.createElement("div");
    meta.className = "habit-meta-row";
    const category = document.createElement("div");
    category.className = "habit-category-badge";
    category.textContent = getCategoryLabel(habit.category);
    const reason = document.createElement("div");
    reason.className = "habit-reason";
    reason.textContent = getReason(habit.category);
    meta.appendChild(category);
    text.appendChild(title);
    text.appendChild(meta);
    text.appendChild(reason);
    main.appendChild(icon);
    main.appendChild(text);
    const actions = document.createElement("div");
    actions.className = "habit-actions";
    const impact = document.createElement("div");
    impact.className = "habit-recovery-impact";
    if (habit.points != null) {
        impact.textContent = `Recovery +${habit.points}`;
    }
    const check = document.createElement("button");
    check.type = "button";
    check.className = "habit-check";
    if (habit.completed) {
        check.classList.add("habit-check-completed");
    }
    check.title = habit.completed
        ? "Відмінити"
        : "Позначити як виконано";
    check.dataset.userHabitId = String(habit.user_habit_id);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "habit-btn-remove";
    remove.textContent = "×";
    remove.title = "Видалити звичку";
    remove.dataset.userHabitId = String(habit.user_habit_id);
    actions.appendChild(impact);
    actions.appendChild(check);
    actions.appendChild(remove);
    item.appendChild(main);
    item.appendChild(actions);
    return item;
}
function createEmptyState() {
    const empty = document.createElement("div");
    empty.className = "db-recovery-empty";
    empty.textContent = "Немає активних звичок";
    return empty;
}
export function renderHabits(snapshot) {
    const countEl = getElement("dashboard-habits");
    const listEl = getElement("dashboard-habits-list");
    if (!countEl || !listEl) {
        return;
    }
    listEl.replaceChildren();
    const habits = Array.isArray(snapshot?.habits)
        ? snapshot.habits.filter((habit) => habit &&
            (habit.user_habit_id !== undefined &&
                habit.user_habit_id !== null))
        : [];
    const completedCount = habits.filter((habit) => habit.completed).length;
    countEl.textContent =
        habits.length > 0
            ? `${completedCount}/${habits.length}`
            : "0";
    if (habits.length === 0) {
        listEl.appendChild(createEmptyState());
        return;
    }
    habits.slice(0, 6).forEach((habit) => {
        listEl.appendChild(createHabitItem(habit));
    });
}
export function bindHabitActions(onRefresh) {
    const listEl = getElement("dashboard-habits-list");
    if (!listEl) {
        return;
    }
    listEl.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        const check = target.closest(".habit-check");
        if (check) {
            const userHabitId = check.dataset.userHabitId;
            if (!userHabitId) {
                return;
            }
            check.disabled = true;
            try {
                await fetch("/api/recovery/habits/logs", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        user_habit_id: userHabitId
                    })
                });
                await onRefresh();
            }
            finally {
                check.disabled = false;
            }
            return;
        }
        const remove = target.closest(".habit-btn-remove");
        if (!remove) {
            return;
        }
        const userHabitId = remove.dataset.userHabitId;
        if (!userHabitId) {
            return;
        }
        remove.disabled = true;
        try {
            await fetch(`/api/recovery/habits/${encodeURIComponent(userHabitId)}`, {
                method: "DELETE"
            });
            await onRefresh();
        }
        finally {
            remove.disabled = false;
        }
    });
}
