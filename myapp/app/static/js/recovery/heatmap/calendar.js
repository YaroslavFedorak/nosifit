import { openDayDetailsModal } from "./day_details_modal.js";

function getMonthName(monthIndex, year) {
    const date = new Date(year, monthIndex, 1);
    return date.toLocaleDateString("uk-UA", { month: "long" });
}

function buildMonthDays(year, month) {
    const days = [];
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const offset = (firstDay.getDay() + 6) % 7;

    for (let i = 0; i < offset; i++) {
        days.push(null);
    }

    for (let d = 1; d <= lastDay.getDate(); d++) {
        const date = new Date(year, month, d);
        days.push(date);
    }

    return days;
}

export function renderRecoveryCalendar(days, year) {
    const body = document.getElementById("rc-calendar-body");
    const title = document.getElementById("rc-calendar-title");

    if (!body || !title) return;

    title.textContent = `Календар відновлення ${year}`;
    body.innerHTML = "";

    const grid = document.createElement("div");
    grid.className = "rc-calendar-grid";

    const byDate = new Map();
    days.forEach(d => {
        if (d?.date) {
            byDate.set(d.date, d);
        }
    });

    for (let month = 0; month < 12; month++) {
        const monthEl = document.createElement("div");
        monthEl.className = "rc-calendar-month";

        const header = document.createElement("div");
        header.className = "rc-calendar-month-header";
        header.textContent = getMonthName(month, year);

        const weekHeader = document.createElement("div");
        weekHeader.className = "rc-calendar-week-header";
        const weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];
        weekdays.forEach(w => {
            const wd = document.createElement("div");
            wd.className = "rc-calendar-weekday";
            wd.textContent = w;
            weekHeader.appendChild(wd);
        });

        const monthBody = document.createElement("div");
        monthBody.className = "rc-calendar-month-body";

        const monthDays = buildMonthDays(year, month);
        monthDays.forEach(date => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "rc-calendar-day";

            if (!date) {
                btn.classList.add("empty");
                monthBody.appendChild(btn);
                return;
            }

            const dayNum = date.getDate();
            btn.textContent = String(dayNum);

            const iso = date.toISOString().slice(0, 10);
            const data = byDate.get(iso);

            if (!data) {
                btn.classList.add("no-data");
            } else {
                const level = Number(data.level) || 0;
                if (level > 0) {
                    btn.dataset.level = String(level);
                }
                btn.addEventListener("click", () => openDayDetailsModal(iso));
            }

            monthBody.appendChild(btn);
        });

        monthEl.appendChild(header);
        monthEl.appendChild(weekHeader);
        monthEl.appendChild(monthBody);
        grid.appendChild(monthEl);
    }

    body.appendChild(grid);
}
