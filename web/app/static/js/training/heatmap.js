import { TrainingAPI } from "./api.js";
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
    "Гру"
];
let CALENDAR_DATA = [];
let CURRENT_YEAR = new Date().getFullYear();
let CURRENT_MONTH = new Date().getMonth();
export function initHeatmap() {
    const yearSelect = document.getElementById("tr-heatmap-year");
    const yearSelectCal = document.getElementById("cal-year-select");
    const openCalendar = document.getElementById("tr-open-calendar");
    const modal = document.getElementById("tr-calendar-modal");
    if (!yearSelect ||
        !yearSelectCal ||
        !openCalendar ||
        !modal) {
        return;
    }
    CURRENT_YEAR =
        Number(yearSelect.value ||
            new Date().getFullYear());
    yearSelectCal.value =
        String(CURRENT_YEAR);
    const load = () => {
        CURRENT_YEAR =
            Number(yearSelect.value);
        yearSelectCal.value =
            String(CURRENT_YEAR);
        TrainingAPI
            .getHeatmap(CURRENT_YEAR)
            .then((data) => {
            CALENDAR_DATA =
                Array.isArray(data?.days)
                    ? data.days
                    : [];
            renderHeatmap(CALENDAR_DATA);
            renderCalendarMonth();
        })
            .catch(() => {
            CALENDAR_DATA = [];
            renderHeatmap([]);
            renderCalendarMonth();
        });
    };
    load();
    yearSelect.addEventListener("change", load);
    yearSelectCal.addEventListener("change", () => {
        CURRENT_YEAR =
            Number(yearSelectCal.value);
        yearSelect.value =
            String(CURRENT_YEAR);
        load();
    });
    openCalendar.addEventListener("click", () => {
        modal.classList.add("open");
    });
    const closeCalendar = document.querySelectorAll("[data-close-calendar]");
    closeCalendar.forEach(button => {
        button.addEventListener("click", () => {
            modal.classList.remove("open");
        });
    });
    const closeDayDetails = document.querySelectorAll("[data-close-day-details]");
    closeDayDetails.forEach(button => {
        button.addEventListener("click", () => {
            const dayModal = document.getElementById("tr-day-details-modal");
            if (dayModal) {
                dayModal.classList.remove("open");
            }
        });
    });
    const prevButton = document.getElementById("cal-prev");
    const nextButton = document.getElementById("cal-next");
    if (prevButton) {
        prevButton.addEventListener("click", () => {
            CURRENT_MONTH -= 1;
            if (CURRENT_MONTH < 0) {
                CURRENT_MONTH = 11;
                CURRENT_YEAR -= 1;
                yearSelect.value =
                    String(CURRENT_YEAR);
                yearSelectCal.value =
                    String(CURRENT_YEAR);
                load();
            }
            else {
                renderCalendarMonth();
            }
        });
    }
    if (nextButton) {
        nextButton.addEventListener("click", () => {
            CURRENT_MONTH += 1;
            if (CURRENT_MONTH > 11) {
                CURRENT_MONTH = 0;
                CURRENT_YEAR += 1;
                yearSelect.value =
                    String(CURRENT_YEAR);
                yearSelectCal.value =
                    String(CURRENT_YEAR);
                load();
            }
            else {
                renderCalendarMonth();
            }
        });
    }
}
function formatDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function renderMonths() {
    const months = document.getElementById("training-heatmap-months");
    if (!months) {
        return;
    }
    months.innerHTML = "";
    MONTHS.forEach(month => {
        const element = document.createElement("span");
        element.textContent =
            month;
        months.appendChild(element);
    });
}
function createEmptyDay(date) {
    return {
        date,
        level: 0,
        percent: 0,
        load: 0,
        is_today: false
    };
}
function renderHeatmap(days) {
    const grid = document.getElementById("training-heatmap");
    if (!grid) {
        return;
    }
    grid.innerHTML = "";
    renderMonths();
    const data = new Map();
    days.forEach(day => {
        if (typeof day.date ===
            "string") {
            data.set(day.date, day);
        }
    });
    const start = new Date(CURRENT_YEAR, 0, 1);
    const end = new Date(CURRENT_YEAR, 11, 31);
    const current = new Date(start);
    while (current <= end) {
        const date = new Date(current);
        const dateString = formatDateKey(date);
        const day = data.get(dateString) ??
            createEmptyDay(dateString);
        let level = Number(day.level);
        if (!Number.isFinite(level)) {
            level = 0;
        }
        level =
            Math.max(0, Math.min(6, Math.round(level)));
        const cell = document.createElement("div");
        cell.className =
            "heatmap-cell";
        cell.dataset.level =
            String(level);
        if (day.is_today) {
            cell.classList.add("today");
        }
        const tooltip = document.createElement("div");
        tooltip.className =
            "heatmap-tooltip";
        tooltip.textContent =
            `${Number(day.percent) || 0}% навантаження (${Number(day.load) || 0} од.)`;
        cell.appendChild(tooltip);
        cell.addEventListener("click", () => {
            openDayDetails(dateString);
        });
        grid.appendChild(cell);
        current.setDate(current.getDate() + 1);
    }
}
function renderCalendarMonth() {
    const grid = document.getElementById("tr-calendar-grid");
    const title = document.getElementById("cal-month-title");
    if (!grid ||
        !title) {
        return;
    }
    grid.innerHTML = "";
    const monthNames = [
        "Січень",
        "Лютий",
        "Березень",
        "Квітень",
        "Травень",
        "Червень",
        "Липень",
        "Серпень",
        "Вересень",
        "Жовтень",
        "Листопад",
        "Грудень"
    ];
    title.textContent =
        `${monthNames[CURRENT_MONTH]} ${CURRENT_YEAR}`;
    const days = CALENDAR_DATA.filter(day => {
        if (!day.date) {
            return false;
        }
        const date = new Date(`${day.date}T12:00:00`);
        return (date.getFullYear() ===
            CURRENT_YEAR &&
            date.getMonth() ===
                CURRENT_MONTH);
    });
    days.forEach(day => {
        if (!day.date) {
            return;
        }
        const item = document.createElement("div");
        item.className =
            `tr-calendar-item tr-level-${day.level ?? 0}`;
        const date = document.createElement("div");
        date.className =
            "tr-calendar-date";
        date.textContent =
            new Date(`${day.date}T12:00:00`)
                .getDate()
                .toString();
        const load = document.createElement("div");
        load.className =
            "tr-calendar-load";
        load.textContent =
            `${day.percent || 0}%`;
        item.appendChild(date);
        item.appendChild(load);
        item.addEventListener("click", () => {
            openDayDetails(day.date);
        });
        grid.appendChild(item);
    });
}
function openDayDetails(date) {
    TrainingAPI
        .getDayDetails(date)
        .then((data) => {
        const modal = document.getElementById("tr-day-details-modal");
        const title = document.getElementById("tr-day-details-title");
        const body = document.getElementById("tr-day-details-body");
        if (!modal ||
            !title ||
            !body) {
            return;
        }
        const parsedDate = new Date(`${date}T12:00:00`);
        title.textContent =
            parsedDate.toLocaleDateString("uk-UA", {
                day: "numeric",
                month: "long",
                year: "numeric"
            });
        const sessions = Array.isArray(data?.sessions)
            ? data.sessions
            : [];
        if (!sessions.length) {
            body.innerHTML =
                "<p>Немає тренувань у цей день</p>";
        }
        else {
            body.innerHTML =
                sessions
                    .map(session => `
                                    <div class="tr-day-session">
                                        <div class="tr-day-session-title">
                                            Сесія
                                        </div>
                                        ${(session.exercises ?? [])
                    .map(exercise => `
                                                    <div class="tr-day-exercise">
                                                        <div class="tr-ex-name">
                                                            ${exercise.name}
                                                        </div>
                                                        <div class="tr-ex-meta">
                                                            ${exercise.sets}×${exercise.reps}, ${exercise.load} кг
                                                        </div>
                                                    </div>
                                                `)
                    .join("")}
                                    </div>
                                `)
                    .join("");
        }
        modal.classList.add("open");
    })
        .catch(() => {
        const modal = document.getElementById("tr-day-details-modal");
        const title = document.getElementById("tr-day-details-title");
        const body = document.getElementById("tr-day-details-body");
        if (title) {
            title.textContent =
                "Помилка";
        }
        if (body) {
            body.innerHTML =
                "<p>Не вдалося завантажити дані.</p>";
        }
        if (modal) {
            modal.classList.add("open");
        }
    });
}
