import { RecoveryAPI } from "../api.js";
import { attachTooltip } from "./tooltip.js";
import { openDayDetailsModal } from "./day_details_modal.js";
import { renderRecoveryCalendar } from "./calendar.js";
import { openCalendarModal, initCalendarModalControls } from "./calendar_modal.js";

function getWeekIndex(date) {
    const yearStart = new Date(date.getFullYear(), 0, 1);
    const dayOffset = (yearStart.getDay() + 6) % 7;
    const firstWeekStart = new Date(yearStart);
    firstWeekStart.setDate(yearStart.getDate() - dayOffset);
    const diffDays = Math.floor((date - firstWeekStart) / (1000 * 60 * 60 * 24));
    return Math.floor(diffDays / 7);
}

export function renderRecoveryHeatmap(days) {
    const grid = document.getElementById("recovery-heatmap");
    const tooltip = document.getElementById("rc-heatmap-tooltip");

    if (!grid || !tooltip) return;

    grid.innerHTML = "";

    const weeks = [];
    for (let i = 0; i < 53; i++) {
        weeks.push(new Array(7).fill(null));
    }

    days.forEach(d => {
        if (!d?.date) return;
        const date = new Date(d.date);
        const dayOfWeek = date.getDay();
        const weekIndex = getWeekIndex(date);
        const level = Number(d.level) || 0;

        if (weekIndex >= 0 && weekIndex < weeks.length) {
            weeks[weekIndex][dayOfWeek] = {
                level,
                date: d.date,
                recovery_score: d.recovery_score
            };
        }
    });

    const todayIso = new Date().toISOString().slice(0, 10);

    weeks.forEach(week => {
        week.forEach(cellData => {
            const cell = document.createElement("div");
            cell.className = "rc-heatmap-cell";

            if (cellData) {
                if (cellData.level > 0) cell.dataset.level = String(cellData.level);
                if (cellData.date === todayIso) cell.classList.add("today");

                attachTooltip(cell, cellData, tooltip);
                cell.addEventListener("click", () => openDayDetailsModal(cellData.date));
            }

            grid.appendChild(cell);
        });
    });
}

export function initRecoveryHeatmap() {
    const root = document.getElementById("recovery-app");
    const yearSelect = document.getElementById("rc-heatmap-year");
    const openCalendarBtn = document.getElementById("rc-open-calendar");

    if (!root || !yearSelect || !openCalendarBtn) return;

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

    const load = () => {
        const year = Number(yearSelect.value || nowYear);
        RecoveryAPI.getHeatmap(userId, year)
            .then(data => {
                const days = Array.isArray(data?.days) ? data.days : [];
                renderRecoveryHeatmap(days);
            })
            .catch(() => {
                renderRecoveryHeatmap([]);
            });
    };

    load();

    yearSelect.addEventListener("change", load);

    openCalendarBtn.addEventListener("click", () => {
        const year = Number(yearSelect.value || nowYear);
        RecoveryAPI.getHeatmap(userId, year)
            .then(data => {
                const days = Array.isArray(data?.days) ? data.days : [];
                renderRecoveryCalendar(days, year);
                openCalendarModal();
            })
            .catch(() => {
                renderRecoveryCalendar([], year);
                openCalendarModal();
            });
    });

    initCalendarModalControls();
}
