import { RECOVERY_MESSAGES } from "./messages.js";
import {
    clearElement,
    createCard,
    createTitle,
    createEmpty
} from "./dom.js";

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

        const left = document.createElement("div");
        left.className = "habit-left";

        const icon = document.createElement("div");
        icon.className = "habit-check";

        const title = document.createElement("div");
        title.className = "habit-title";
        title.textContent = habit.name;

        const meta = document.createElement("div");
        meta.className = "habit-meta";
        meta.textContent = habit.category;

        left.appendChild(icon);
        left.appendChild(title);
        left.appendChild(meta);

        const points = document.createElement("div");
        points.textContent = `+${habit.points}`;

        item.appendChild(left);
        item.appendChild(points);

        list.appendChild(item);
    });

    card.appendChild(list);
    el.appendChild(card);
}
