import { formatDateLong } from "../formatters.js";
import { createDayCard } from "./day_card.js";

export function openDayDetailsModal(dateIso) {
    const modal = document.getElementById("rc-day-details-modal");
    const title = document.getElementById("rc-day-details-title");
    const body = document.getElementById("rc-day-details-body");

    if (!modal || !title || !body) return;

    title.textContent = formatDateLong(dateIso);

    body.innerHTML = "";

    modal.classList.add("open");
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
