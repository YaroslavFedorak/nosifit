import { RecoveryAPI } from "../api.js";
import { attachTooltip } from "./tooltip.js";
import { openDayDetailsModal } from "./day_details/modal.js";
import { renderRecoveryCalendar } from "./calendar.js";
import { openCalendarModal, initCalendarModalControls } from "./calendar_modal.js";

const DAYS = 7;
const MS_DAY = 1000 * 60 * 60 * 24;

function localIso(date) {
  const d = new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function daysInYear(year) {
  const start = new Date(year, 0, 1);
  const next = new Date(year + 1, 0, 1);
  return Math.round((next.getTime() - start.getTime()) / MS_DAY);
}

export function renderRecoveryHeatmap(days, yearOverride) {
  const grid = document.getElementById("recovery-heatmap");
  if (!grid) return;
  grid.innerHTML = "";

  const year = typeof yearOverride === "number"
    ? yearOverride
    : Array.isArray(days) && days.length && days[0]?.date
      ? new Date(days[0].date).getFullYear()
      : new Date().getFullYear();

  const jan1 = new Date(year, 0, 1);
  jan1.setHours(0, 0, 0, 0);
  const totalDays = daysInYear(year);
  const neededCols = Math.ceil(totalDays / DAYS);

  const daysMap = {};
  if (Array.isArray(days)) {
    days.forEach(d => {
      if (!d?.date) return;
      const iso = localIso(d.date);
      daysMap[iso] = {
        level: Number(d.level) || 0,
        date: iso,
        recovery_score: d.recovery_score ?? 0,
        percent: d.percent ?? 0,
        load: d.load ?? 0,
        is_today: !!d.is_today
      };
    });
  }

  grid.style.gridTemplateColumns = `repeat(${neededCols}, var(--rc-cell-size))`;

  const todayIso = localIso(new Date());

  for (let i = 0; i < totalDays; i++) {
    const current = new Date(jan1.getTime() + i * MS_DAY);
    const iso = localIso(current);
    const entry = daysMap[iso] ?? {
      level: 0,
      date: iso,
      recovery_score: 0,
      percent: 0,
      load: 0,
      is_today: iso === todayIso
    };
    const cell = document.createElement("div");
    cell.className = "rc-heatmap-cell";
    cell.dataset.level = String(entry.level ?? 0);
    if ((entry.date && localIso(entry.date) === todayIso) || entry.is_today) cell.classList.add("today");
    attachTooltip(cell, entry);
    cell.addEventListener("click", () => openDayDetailsModal(entry.date));
    grid.appendChild(cell);
  }
}

export function initRecoveryHeatmap() {
  const root = document.getElementById("recovery-app");
  const yearSelect = document.getElementById("rc-heatmap-year");
  const openCalendarBtn = document.getElementById("rc-open-calendar");
  const calYearSelect = document.getElementById("rc-cal-year-select");

  if (!root || !yearSelect || !openCalendarBtn) return;

  const userId = Number(root.dataset.userId || 0);
  if (!userId) return;

  const nowYear = new Date().getFullYear();
  yearSelect.innerHTML = "";
  if (calYearSelect) calYearSelect.innerHTML = "";
  for (let y = nowYear; y >= 2020; y--) {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    yearSelect.appendChild(opt);
    if (calYearSelect) {
      const opt2 = document.createElement("option");
      opt2.value = String(y);
      opt2.textContent = String(y);
      calYearSelect.appendChild(opt2);
    }
  }

  const load = () => {
    const year = Number(yearSelect.value || nowYear);
    RecoveryAPI.getHeatmap(userId, year)
      .then(data => {
        const days = Array.isArray(data?.days) ? data.days : [];
        renderRecoveryHeatmap(days, year);
      })
      .catch(() => {
        renderRecoveryHeatmap([], Number(yearSelect.value || nowYear));
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

  const closeCalendarBtns = document.querySelectorAll("[data-close-calendar]");
  closeCalendarBtns.forEach(btn => btn.addEventListener("click", () => {
    const modal = document.getElementById("rc-calendar-modal");
    if (modal) modal.classList.remove("open");
  }));

  const closeDayDetailsBtns = document.querySelectorAll("[data-close-day-details]");
  closeDayDetailsBtns.forEach(btn => btn.addEventListener("click", () => {
    const m = document.getElementById("rc-day-details-modal");
    if (m) m.classList.remove("open");
  }));

  if (calYearSelect) {
    calYearSelect.addEventListener("change", () => {
      const selYear = Number(calYearSelect.value);
      yearSelect.value = selYear;
      yearSelect.dispatchEvent(new Event("change"));
    });
  }

  initCalendarModalControls();
}
