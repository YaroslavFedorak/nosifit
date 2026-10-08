import { RecoveryAPI } from "../api.js";
import { recovery_t } from "../../i18n/index.js";
import { attachTooltip } from "./tooltip.js";
import { openDayDetails } from "./day_details/modal.js";
const MONTHS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec"
];
const MS_DAY = 1000 *
    60 *
    60 *
    24;
function localIso(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
function daysInYear(year) {
    const start = new Date(year, 0, 1);
    const next = new Date(year + 1, 0, 1);
    return Math.round((next.getTime() -
        start.getTime()) / MS_DAY);
}
function renderMonths() {
    const months = document.getElementById("recovery-heatmap-months");
    if (!months) {
        return;
    }
    months.replaceChildren();
    MONTHS.forEach(month => {
        const element = document.createElement("span");
        element.textContent =
            recovery_t(`heatmap.months.${month}`);
        months.appendChild(element);
    });
}
function normalizeLevel(value) {
    const level = Number(value);
    if (!Number.isFinite(level)) {
        return 0;
    }
    return Math.max(0, Math.min(4, Math.round(level)));
}
function normalizeDay(day, date, today) {
    return {
        date,
        level: normalizeLevel(day.level),
        recovery_score: day.recovery_score ??
            null,
        percent: day.percent ??
            null,
        load: day.load ??
            null,
        is_today: Boolean(day.is_today) ||
            date === today
    };
}
function createCell(day, date, today) {
    const cell = document.createElement("div");
    cell.className =
        "rc-heatmap-cell";
    cell.dataset.date =
        date;
    cell.dataset.level =
        String(normalizeLevel(day.level));
    cell.setAttribute("role", "gridcell");
    cell.setAttribute("tabindex", "0");
    const scoreLabel = day.recovery_score == null
        ? recovery_t("heatmap.no_data")
        : recovery_t("heatmap.score", {
            score: Math.round(day.recovery_score)
        });
    cell.setAttribute("aria-label", `${date}: ${scoreLabel}`);
    if (day.is_today ||
        date === today) {
        cell.classList.add("today");
    }
    attachTooltip(cell, day);
    cell.addEventListener("click", () => {
        openDayDetails(date);
    });
    cell.addEventListener("keydown", event => {
        if (event.key !== "Enter" &&
            event.key !== " ") {
            return;
        }
        event.preventDefault();
        openDayDetails(date);
    });
    return cell;
}
export function renderRecoveryHeatmap(days, yearOverride) {
    const grid = document.getElementById("recovery-heatmap");
    if (!grid) {
        return;
    }
    const year = typeof yearOverride === "number"
        ? yearOverride
        : new Date().getFullYear();
    const totalDays = daysInYear(year);
    const daysMap = new Map();
    const today = localIso(new Date());
    days.forEach(day => {
        if (!day?.date) {
            return;
        }
        const parsed = new Date(`${day.date}T12:00:00`);
        if (Number.isNaN(parsed.getTime())) {
            return;
        }
        const date = localIso(parsed);
        daysMap.set(date, normalizeDay(day, date, today));
    });
    grid.replaceChildren();
    grid.style.gridTemplateColumns =
        `repeat(${Math.ceil(totalDays / 7)}, minmax(0, 1fr))`;
    renderMonths();
    const fragment = document.createDocumentFragment();
    for (let index = 0; index < totalDays; index++) {
        const current = new Date(year, 0, 1);
        current.setDate(current.getDate() +
            index);
        const date = localIso(current);
        const day = daysMap.get(date) ??
            normalizeDay({}, date, today);
        fragment.appendChild(createCell(day, date, today));
    }
    grid.appendChild(fragment);
}
export function renderHeatmapWidget(data, options = {}) {
    const grid = document.getElementById("recovery-heatmap");
    if (!grid) {
        return;
    }
    if (options.loading) {
        grid.replaceChildren();
        renderMonths();
        return;
    }
    renderRecoveryHeatmap(Array.isArray(data?.days)
        ? data.days
        : []);
}
export function initRecoveryHeatmap() {
    const root = document.getElementById("recovery-app");
    const yearSelect = document.getElementById("rc-heatmap-year");
    if (!root ||
        !yearSelect) {
        return;
    }
    const userId = Number(root.dataset.userId ||
        0);
    if (!Number.isFinite(userId) ||
        userId <= 0) {
        return;
    }
    const currentYear = new Date().getFullYear();
    yearSelect.replaceChildren();
    for (let year = currentYear; year >= 2020; year--) {
        const option = document.createElement("option");
        option.value =
            String(year);
        option.textContent =
            String(year);
        yearSelect.appendChild(option);
    }
    yearSelect.value =
        String(currentYear);
    const load = async () => {
        const year = Number(yearSelect.value);
        if (!Number.isFinite(year)) {
            return;
        }
        try {
            const data = await RecoveryAPI.getHeatmap(userId, year);
            renderRecoveryHeatmap(Array.isArray(data?.days)
                ? data.days
                : [], year);
        }
        catch {
            renderRecoveryHeatmap([], year);
        }
    };
    yearSelect.addEventListener("change", () => {
        void load();
    });
    void load();
}
