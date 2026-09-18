const MONTHS = [
    "Січ",
    "Лют",
    "Бер",
    "Кві",
    "Тра",
    "Чер",
    "Лип",
    "Сер",
    "Вер",
    "Жов",
    "Лис",
    "Гру",
];
function formatDate(dateString) {
    const date = new Date(`${dateString}T12:00:00`);
    return date.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}
function formatDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function createTooltip(day) {
    const tooltip = document.createElement("div");
    tooltip.className =
        "heatmap-tooltip";
    const date = document.createElement("strong");
    date.textContent =
        day.date
            ? formatDate(day.date)
            : "Немає даних";
    const score = document.createElement("span");
    score.textContent =
        day.daily_score == null
            ? "Баланс дня —"
            : `Баланс дня ${day.daily_score}`;
    const training = document.createElement("span");
    training.textContent =
        day.training?.score == null
            ? "Тренування —"
            : `Тренування ${day.training.score}`;
    const recovery = document.createElement("span");
    recovery.textContent =
        day.recovery?.score == null
            ? "Відновлення —"
            : `Відновлення ${day.recovery.score}`;
    const nutrition = document.createElement("span");
    nutrition.textContent =
        day.nutrition?.score == null
            ? "Харчування —"
            : `Харчування ${day.nutrition.score}`;
    tooltip.append(date, score, training, recovery, nutrition);
    return tooltip;
}
function createCell(day) {
    const cell = document.createElement("div");
    cell.className =
        "heatmap-cell";
    const level = typeof day.level === "number"
        ? Math.max(0, Math.min(6, Math.round(day.level)))
        : 0;
    cell.dataset.level =
        String(level);
    if (day.date) {
        cell.dataset.date =
            day.date;
    }
    const todayKey = formatDateKey(new Date());
    if (day.date === todayKey) {
        cell.classList.add("today");
    }
    cell.setAttribute("role", "gridcell");
    if (day.date) {
        cell.setAttribute("aria-label", `${formatDate(day.date)}, баланс дня ${day.daily_score ?? "немає даних"}`);
        cell.appendChild(createTooltip(day));
        cell.addEventListener("click", () => {
            document.dispatchEvent(new CustomEvent("dashboard:open-day", {
                detail: day,
            }));
        });
    }
    return cell;
}
function getMonthColumn(year, month) {
    const firstDate = new Date(year, 0, 1);
    const monthDate = new Date(year, month, 1);
    const firstDay = firstDate.getDay();
    const firstOffset = firstDay === 0
        ? 6
        : firstDay - 1;
    const daysFromStart = Math.round((monthDate.getTime() -
        firstDate.getTime()) /
        86400000);
    return Math.floor((firstOffset +
        daysFromStart) /
        7);
}
function renderMonths(year) {
    const months = document.getElementById("dashboard-heatmap-months");
    if (!months) {
        return;
    }
    months.innerHTML =
        "";
    for (let month = 0; month < 12; month += 1) {
        const element = document.createElement("span");
        element.textContent =
            MONTHS[month];
        element.dataset.month =
            String(month);
        const column = getMonthColumn(year, month);
        element.style.gridColumn =
            `${column + 1}`;
        months.appendChild(element);
    }
}
function buildDayMap(data) {
    const map = new Map();
    if (!data ||
        !Array.isArray(data.days)) {
        return map;
    }
    data.days.forEach((day) => {
        if (typeof day.date !==
            "string") {
            return;
        }
        map.set(day.date, day);
    });
    return map;
}
function createEmptyDay(date) {
    return {
        date,
        daily_score: null,
        level: 0,
        training: {
            score: null,
        },
        recovery: {
            score: null,
        },
        nutrition: {
            score: null,
        },
    };
}
function renderGrid(container, data) {
    container.innerHTML =
        "";
    const year = new Date().getFullYear();
    const dayMap = buildDayMap(data);
    const firstDate = new Date(year, 0, 1);
    const current = new Date(firstDate);
    const lastDate = new Date(year, 11, 31);
    while (current <= lastDate) {
        const dateString = formatDateKey(current);
        const day = dayMap.get(dateString) ??
            createEmptyDay(dateString);
        container.appendChild(createCell(day));
        current.setDate(current.getDate() + 1);
    }
    renderMonths(year);
}
export function renderHeatmap(container, data) {
    renderGrid(container, data);
}
