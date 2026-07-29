import { formatTooltipDay } from "./formatters.js";

function positionTooltip(event, tooltipEl) {
    const x = event.clientX + 12;
    const y = event.clientY - 12;
    tooltipEl.style.left = `${x}px`;
    tooltipEl.style.top = `${y}px`;
}

export function attachTooltip(cell, data, tooltipEl) {
    if (!cell || !tooltipEl || !data) return;

    cell.addEventListener("mouseenter", event => {
        tooltipEl.textContent = formatTooltipDay(data.date, data.recovery_score);
        tooltipEl.classList.add("visible");
        positionTooltip(event, tooltipEl);
    });

    cell.addEventListener("mousemove", event => {
        positionTooltip(event, tooltipEl);
    });

    cell.addEventListener("mouseleave", () => {
        tooltipEl.classList.remove("visible");
    });
}
