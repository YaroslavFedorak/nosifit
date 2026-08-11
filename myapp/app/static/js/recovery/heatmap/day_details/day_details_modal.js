import { RecoveryAPI } from "../../api.js";
import { formatDateLong } from "../formatters.js";
import { renderDayDetails } from "./day_details_renderer.js";

export async function openDayDetailsModal(dateIso) {
    const modal = document.getElementById("rc-day-details-modal");
    const title = document.getElementById("rc-day-details-title");
    const body = document.getElementById("rc-day-details-body");

    if (!modal || !title || !body) return;

    title.textContent = formatDateLong(dateIso);
    body.innerHTML = `<div class="rc-list-item">Завантаження...</div>`;

    modal.classList.add("open");

    const root = document.getElementById("recovery-app");
    const userId = Number(root?.dataset?.userId || 0);

    let raw = null;
    try {
        raw = await RecoveryAPI.getDayDetails(userId, dateIso);
    } catch (e) {
        console.warn("DayDetails API error:", e);
    }

    const data = normalize(raw, dateIso);

    body.innerHTML = "";
    renderDayDetails(body, data);
}

export function initDayDetailsModalControls() {
    const buttons = document.querySelectorAll("[data-close-day-details]");
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const modal = document.getElementById("rc-day-details-modal");
            if (modal) modal.classList.remove("open");
        });
    });
}

function normalize(raw, dateIso) {
    if (!raw) return { has_data: false };

    return {
        date: dateIso,
        has_data: raw.has_data ?? true,
        recovery: raw.recovery ?? {},
        sleep: raw.sleep ?? {},
        training: raw.training ?? {},
        habits: raw.habits ?? {},
        recommendations: raw.recommendations ?? {}
    };
}
