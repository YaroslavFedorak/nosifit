import { TrainingAPI } from "./api.js";

let CALENDAR_DATA = [];
let CURRENT_YEAR = new Date().getFullYear();
let CURRENT_MONTH = new Date().getMonth();

export function initHeatmap() {
    const yearSelect = document.getElementById("tr-heatmap-year");
    const yearSelectCal = document.getElementById("cal-year-select");
    const openCalendar = document.getElementById("tr-open-calendar");
    const modal = document.getElementById("tr-calendar-modal");

    if (!yearSelect || !yearSelectCal || !openCalendar || !modal) return;

    CURRENT_YEAR = Number(yearSelect.value || new Date().getFullYear());
    yearSelectCal.value = CURRENT_YEAR;

    const load = () => {
        CURRENT_YEAR = Number(yearSelect.value);
        yearSelectCal.value = CURRENT_YEAR;

        TrainingAPI.getHeatmap(CURRENT_YEAR)
            .then(data => {
                CALENDAR_DATA = Array.isArray(data?.days) ? data.days : [];
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
        CURRENT_YEAR = Number(yearSelectCal.value);
        yearSelect.value = CURRENT_YEAR;
        load();
    });

    openCalendar.addEventListener("click", () => modal.classList.add("open"));

    const closeCalendar = document.querySelectorAll("[data-close-calendar]");
    closeCalendar.forEach(btn =>
        btn.addEventListener("click", () => modal.classList.remove("open"))
    );

    const closeDayDetails = document.querySelectorAll("[data-close-day-details]");
    closeDayDetails.forEach(btn =>
        btn.addEventListener("click", () => {
            const m = document.getElementById("tr-day-details-modal");
            if (m) m.classList.remove("open");
        })
    );

    const prevBtn = document.getElementById("cal-prev");
    const nextBtn = document.getElementById("cal-next");

    if (prevBtn) {
        prevBtn.addEventListener("click", () => {
            CURRENT_MONTH--;
            if (CURRENT_MONTH < 0) {
                CURRENT_MONTH = 11;
                CURRENT_YEAR--;
                yearSelect.value = CURRENT_YEAR;
                yearSelectCal.value = CURRENT_YEAR;
                load();
            } else {
                renderCalendarMonth();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", () => {
            CURRENT_MONTH++;
            if (CURRENT_MONTH > 11) {
                CURRENT_MONTH = 0;
                CURRENT_YEAR++;
                yearSelect.value = CURRENT_YEAR;
                yearSelectCal.value = CURRENT_YEAR;
                load();
            } else {
                renderCalendarMonth();
            }
        });
    }
}

function renderHeatmap(days) {
    const grid = document.getElementById("training-heatmap");

    if (!grid) return;

    grid.innerHTML = "";

    const data = new Map(
        days.map(day => [
            day.date,
            day,
        ])
    );

    const start = new Date(CURRENT_YEAR, 0, 1);
    const end = new Date(CURRENT_YEAR, 11, 31);

    const current = new Date(start);

    while (current <= end) {
        const date = new Date(current);
        const dateString = date.toISOString().slice(0, 10);

        const day = data.get(dateString) || {
            date: dateString,
            level: 0,
            percent: 0,
            load: 0,
            is_today: false,
        };

        let level = Number(day.level);

        if (!Number.isFinite(level)) {
            level = 0;
        }

        level = Math.max(0, Math.min(6, Math.round(level)));

        const cell = document.createElement("div");

        cell.className = "heatmap-cell";
        cell.dataset.level = String(level);

        if (day.is_today) {
            cell.classList.add("today");
        }

        const tooltip = document.createElement("div");

        tooltip.className = "heatmap-tooltip";

        tooltip.textContent =
            `${Number(day.percent) || 0}% навантаження (${Number(day.load) || 0} од.)`;

        cell.appendChild(tooltip);

        cell.addEventListener(
            "click",
            () => openDayDetails(dateString)
        );

        grid.appendChild(cell);

        current.setDate(current.getDate() + 1);
    }
}


function renderCalendarMonth() {
    const grid = document.getElementById("tr-calendar-grid");
    const title = document.getElementById("cal-month-title");
    if (!grid || !title) return;

    grid.innerHTML = "";

    const monthNames = [
        "Січень","Лютий","Березень","Квітень","Травень","Червень",
        "Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"
    ];

    title.textContent = `${monthNames[CURRENT_MONTH]} ${CURRENT_YEAR}`;

    const days = CALENDAR_DATA.filter(d => {
        const dt = new Date(d.date);
        return dt.getFullYear() === CURRENT_YEAR && dt.getMonth() === CURRENT_MONTH;
    });

    days.forEach(d => {
        const item = document.createElement("div");
        item.className = "tr-calendar-item tr-level-" + d.level;

        const date = document.createElement("div");
        date.className = "tr-calendar-date";
        date.textContent = new Date(d.date).getDate();

        const load = document.createElement("div");
        load.className = "tr-calendar-load";
        load.textContent = `${d.percent || 0}%`;

        item.appendChild(date);
        item.appendChild(load);

        item.addEventListener("click", () => openDayDetails(d.date));

        grid.appendChild(item);
    });
}

function openDayDetails(date) {
    TrainingAPI.getDayDetails(date)
        .then(data => {
            const modal = document.getElementById("tr-day-details-modal");
            const title = document.getElementById("tr-day-details-title");
            const body = document.getElementById("tr-day-details-body");
            if (!modal || !title || !body) return;

            const dt = new Date(date).toLocaleDateString("uk-UA", {
                day: "numeric",
                month: "long",
                year: "numeric"
            });

            title.textContent = dt;

            const sessions = Array.isArray(data?.sessions) ? data.sessions : [];

            if (!sessions.length) {
                body.innerHTML = "<p>Немає тренувань у цей день</p>";
            } else {
                body.innerHTML = sessions
                    .map(s => `
                        <div class="tr-day-session">
                            <div class="tr-day-session-title">Сесія</div>
                            ${s.exercises
                                .map(ex => `
                                    <div class="tr-day-exercise">
                                        <div class="tr-ex-name">${ex.name}</div>
                                        <div class="tr-ex-meta">${ex.sets}×${ex.reps}, ${ex.load} кг</div>
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

            if (title) title.textContent = "Помилка";
            if (body) body.innerHTML = "<p>Не вдалося завантажити дані.</p>";
            if (modal) modal.classList.add("open");
        });
}
