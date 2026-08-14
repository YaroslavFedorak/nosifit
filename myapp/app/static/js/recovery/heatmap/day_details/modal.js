import { RecoveryAPI } from "../../api.js";
import { formatDateLong, formatWeekday } from "../formatters.js";
import { renderDayDetailsBody } from "./renderer.js";

export async function openDayDetailsModal(dateIso) {
  const modal = document.getElementById("rc-day-details-modal");
  const dialog = modal?.querySelector(".rc-day-details-dialog");
  const title = dialog?.querySelector("#rc-day-details-title");
  const subtitle = dialog?.querySelector("#rc-day-details-subtitle");
  const body = dialog?.querySelector("#rc-day-details-body");

  if (!modal || !dialog || !title || !subtitle || !body) return;

  title.textContent = formatDateLong(dateIso);
  subtitle.textContent = formatWeekday(dateIso);
  body.innerHTML = "";

  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");

  const root = document.getElementById("recovery-app");
  const userId = Number(root?.dataset?.userId || 0);

  const loading = document.createElement("div");
  loading.className = "rc-day-daily-summary";
  loading.textContent = "Завантаження…";
  body.appendChild(loading);

  let raw = null;
  try {
    raw = await RecoveryAPI.getDayDetails(userId, dateIso);
  } catch {
    raw = null;
  }

  const data = normalize(raw, dateIso);
  body.innerHTML = "";
  renderDayDetailsBody(body, data);
}

export function initDayDetailsModalControls() {
  const closeBtns = document.querySelectorAll("[data-close-day-details]");
  closeBtns.forEach(btn => btn.addEventListener("click", () => {
    const modal = document.getElementById("rc-day-details-modal");
    if (modal) {
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
    }
  }));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const modal = document.getElementById("rc-day-details-modal");
      if (modal && modal.classList.contains("open")) {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
      }
    }
  });
}

function normalize(raw, dateIso) {
  if (!raw) {
    return {
      date: dateIso,
      has_data: false,
      recovery: { score: null, status: null, energy_score: null },
      sleep: { duration_minutes: null, quality_score: null },
      training: { load: null, sessions: 0, exercises: [] },
      habits: { completed: 0, total: 0, score: null, items: [] },
      recommendations: { items: [], total: 0 }
    };
  }

  return {
    date: raw.date || dateIso,
    has_data: raw.has_data ?? true,
    recovery: raw.recovery ?? {},
    sleep: raw.sleep ?? {},
    training: raw.training ?? {},
    habits: raw.habits ?? {},
    recommendations: raw.recommendations ?? {}
  };
}
