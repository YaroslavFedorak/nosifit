import { RecoveryAPI } from "../api.js";
import { attachTooltip } from "./tooltip.js";
import { openDayDetails } from "./day_details.js";
import { ICONS } from "../../icons/icons.js";

let HEATMAP_DATA = [];
let CURRENT_YEAR = new Date().getFullYear();

export function initRecoveryHeatmap() {
    const root = document.getElementById("recovery-app");
    const yearSelect = document.getElementById("rc-heatmap-year");
    const openCalendar = document.getElementById("rc-open-calendar");
    const modal = document.getElementById("rc-calendar-modal");
    const grid = document.getElementById("recovery-heatmap");
    const tooltip = document.getElementById("rc-heatmap-tooltip");

    if (!root || !yearSelect || !openCalendar || !grid || !tooltip) return;

    const userId = Number(root.dataset.userId || 0);
    if (!userId) return;

    const nowYear = new Date().getFullYear();
    yearSelect.innerHTML = "";
    for (let y = nowYear; y >= 2020; y--) {
        const opt = document.createElement("option");
        opt.value = String(y);
        opt.textContent = String(y);
        yearSelect.appendChild(opt);
    }

    CURRENT_YEAR = Number(yearSelect.value || nowYear);

    const load = () => {
        CURRENT_YEAR = Number(yearSelect.value);
        RecoveryAPI.getHeatmap(userId, CURRENT_YEAR)
            .then(data => {
                HEATMAP_DATA = Array.isArray(data?.days) ? data.days : [];
                renderRecoveryHeatmap(HEATMAP_DATA, grid, tooltip);
                renderRecoveryCalendar(HEATMAP_DATA);
            })
            .catch(() => {
                HEATMAP_DATA = [];
                renderRecoveryHeatmap([], grid, tooltip);
                renderRecoveryCalendar([]);
            });
    };

    load();
    yearSelect.addEventListener("change", load);

    openCalendar.addEventListener("click", () => {
        renderRecoveryCalendar(HEATMAP_DATA);
        if (modal) modal.classList.add("open");
    });

    const closeCalendar = document.querySelectorAll("[data-close-calendar]");
    closeCalendar.forEach(btn =>
        btn.addEventListener("click", () => {
            if (modal) modal.classList.remove("open");
        })
    );

    const closeDayDetails = document.querySelectorAll("[data-close-day-details]");
    closeDayDetails.forEach(btn =>
        btn.addEventListener("click", () => {
            const dayModal = document.getElementById("rc-day-details-modal");
            if (dayModal) dayModal.classList.remove("open");
        })
    );
}

export function renderRecoveryHeatmap(days, grid, tooltip) {
    if (!grid || !tooltip) return;

    grid.innerHTML = "";

    const weeks = [];
    for (let i = 0; i < 53; i++) {
        weeks.push(new Array(7).fill(null));
    }

    days.forEach(d => {
        const date = new Date(d.date);
        const dayOfWeek = date.getDay();
        const weekIndex = getWeekIndex(date);
        const level = Number(d.level) || 0;

        if (weekIndex >= 0 && weekIndex < weeks.length) {
            weeks[weekIndex][dayOfWeek] = {
                level,
                date: d.date,
                recovery_score: d.recovery_score,
                sleep_score: d.sleep_score,
                energy_score: d.energy_score
            };
        }
    });

    weeks.forEach(week => {
        week.forEach(cellData => {
            const cell = document.createElement("div");
            cell.className = "rc-heatmap-cell";

            if (cellData) {
                cell.dataset.level = String(cellData.level);

                cell.addEventListener("mouseenter", e => {
                    tooltip.textContent = formatTooltip(cellData);
                    tooltip.classList.add("visible");
                    positionTooltip(e, tooltip);
                });

                cell.addEventListener("mousemove", e => {
                    positionTooltip(e, tooltip);
                });

                cell.addEventListener("mouseleave", () => {
                    tooltip.classList.remove("visible");
                });

                cell.addEventListener("click", () => openRecoveryDay(cellData.date));
            }

            grid.appendChild(cell);
        });
    });
}

function formatTooltip(cellData) {
    const date = new Date(cellData.date);
    const dateStr = date.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "short"
    });

    const recovery = cellData.recovery_score ?? "—";
    const sleep = cellData.sleep_score ?? null;
    const energy = cellData.energy_score ?? null;

    let lines = [`${dateStr}`, `Recovery: ${recovery}`];

    if (sleep != null) {
        lines.push(`Sleep: ${sleep}`);
    }
    if (energy != null) {
        lines.push(`Energy: ${energy}`);
    }

    return lines.join(" · ");
}

function positionTooltip(event, tooltip) {
    const x = event.clientX + 12;
    const y = event.clientY - 12;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

function getWeekIndex(date) {
    const yearStart = new Date(date.getFullYear(), 0, 1);
    const dayOffset = (yearStart.getDay() + 6) % 7;
    const firstWeekStart = new Date(yearStart);
    firstWeekStart.setDate(yearStart.getDate() - dayOffset);
    const diffDays = Math.floor(
        (date.getTime() - firstWeekStart.getTime()) / (1000 * 60 * 60 * 24)
    );
    return Math.floor(diffDays / 7);
}

function renderRecoveryCalendar(days) {
    const body = document.getElementById("rc-calendar-body");
    const title = document.getElementById("rc-calendar-title");
    if (!body || !title) return;

    body.innerHTML = "";

    const year = CURRENT_YEAR;
    const months = Array.from({ length: 12 }, (_, i) => i);

    const container = document.createElement("div");
    container.className = "rc-calendar-grid";

    title.textContent = `Recovery Calendar ${year}`;

    const byDate = new Map();
    days.forEach(d => {
        byDate.set(d.date, d);
    });

    months.forEach(monthIndex => {
        const monthDate = new Date(year, monthIndex, 1);
        const monthName = monthDate.toLocaleDateString("uk-UA", {
            month: "long"
        });

        const monthBlock = document.createElement("div");
        monthBlock.className = "rc-calendar-month";

        const monthHeader = document.createElement("div");
        monthHeader.className = "rc-calendar-month-header";
        monthHeader.textContent = monthName;

        const weekHeader = document.createElement("div");
        weekHeader.className = "rc-calendar-week-header";
        ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].forEach(dow => {
            const cell = document.createElement("div");
            cell.className = "rc-calendar-weekday";
            cell.textContent = dow;
            weekHeader.appendChild(cell);
        });

        const monthBody = document.createElement("div");
        monthBody.className = "rc-calendar-month-body";

        const firstDay = new Date(year, monthIndex, 1);
        const startOffset = (firstDay.getDay() + 6) % 7;
        for (let i = 0; i < startOffset; i++) {
            const emptyCell = document.createElement("button");
            emptyCell.className = "rc-calendar-day empty";
            emptyCell.disabled = true;
            monthBody.appendChild(emptyCell);
        }

        const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
        for (let day = 1; day <= daysInMonth; day++) {
            const dateObj = new Date(year, monthIndex, day);
            const iso = dateObj.toISOString().slice(0, 10);
            const data = byDate.get(iso) || null;

            const dayBtn = document.createElement("button");
            dayBtn.className = "rc-calendar-day";

            if (data && typeof data.level === "number") {
                dayBtn.dataset.level = String(data.level);
            }

            const label = document.createElement("span");
            label.className = "rc-calendar-day-label";
            label.textContent = String(day);

            dayBtn.appendChild(label);

            if (data) {
                dayBtn.addEventListener("click", () => openRecoveryDay(iso));
            } else {
                dayBtn.classList.add("no-data");
            }

            monthBody.appendChild(dayBtn);
        }

        monthBlock.appendChild(monthHeader);
        monthBlock.appendChild(weekHeader);
        monthBlock.appendChild(monthBody);
        container.appendChild(monthBlock);
    });

    body.appendChild(container);
}

function openRecoveryDay(date) {
    const root = document.getElementById("recovery-app");
    if (!root) return;

    const userId = Number(root.dataset.userId || 0);
    if (!userId) return;

    RecoveryAPI.getSnapshot(userId, date)
        .then(snapshot => {
            const modal = document.getElementById("rc-day-details-modal");
            const title = document.getElementById("rc-day-details-title");
            const body = document.getElementById("rc-day-details-body");
            if (!modal || !title || !body) return;

            const dt = new Date(date).toLocaleDateString("uk-UA", {
                day: "numeric",
                month: "long",
                year: "numeric"
            });
            title.textContent = dt;

            body.innerHTML = "";

            if (!snapshot) {
                const p = document.createElement("p");
                p.textContent = "Немає даних за цей день";
                body.appendChild(p);
            } else {
                const wrapper = document.createElement("div");
                wrapper.className = "rc-day-info";

                wrapper.appendChild(createDayCard(ICONS.heart_pulse, "Recovery", snapshot.recovery_score));
                wrapper.appendChild(createDayCard(ICONS.moon, "Sleep", snapshot.sleep_score));
                wrapper.appendChild(createDayCard(ICONS.exercise, "Training", snapshot.training_score));
                wrapper.appendChild(createDayCard(ICONS.habits, "Habits", snapshot.habit_score));
                wrapper.appendChild(createDayCard(ICONS.energy, "Energy", snapshot.energy_score));

                body.appendChild(wrapper);
            }

            modal.classList.add("open");
        })
        .catch(() => {
            const modal = document.getElementById("rc-day-details-modal");
            const title = document.getElementById("rc-day-details-title");
            const body = document.getElementById("rc-day-details-body");
            if (title) title.textContent = "Помилка";
            if (body) {
                body.innerHTML = "";
                const p = document.createElement("p");
                p.textContent = "Не вдалося завантажити дані.";
                body.appendChild(p);
            }
            if (modal) modal.classList.add("open");
        });
}

function createDayCard(iconSvg, label, value) {
    const card = document.createElement("div");
    card.className = "rc-day-card";

    const header = document.createElement("div");
    header.className = "rc-day-card-header";

    const icon = document.createElement("span");
    icon.className = "rc-day-card-icon";
    icon.innerHTML = iconSvg;

    const title = document.createElement("span");
    title.className = "rc-day-card-title";
    title.textContent = label;

    header.appendChild(icon);
    header.appendChild(title);

    const score = document.createElement("div");
    score.className = "rc-day-card-score";
    score.textContent = value != null ? value : "—";

    card.appendChild(header);
    card.appendChild(score);

    return card;
}
