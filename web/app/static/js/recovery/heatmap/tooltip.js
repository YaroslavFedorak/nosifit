import { formatTooltipDayHTML } from "./formatters.js";
export function attachTooltip(cell, data) {
    const tooltip = document.createElement("div");
    tooltip.className =
        "rc-heatmap-tooltip";
    tooltip.setAttribute("role", "tooltip");
    tooltip.setAttribute("aria-hidden", "true");
    tooltip.innerHTML =
        formatTooltipDayHTML({
            date: data.date ??
                null,
            recovery_score: data.recovery_score ??
                null
        });
    cell.appendChild(tooltip);
    const show = () => {
        tooltip.classList.add("visible");
        tooltip.setAttribute("aria-hidden", "false");
    };
    const hide = () => {
        tooltip.classList.remove("visible");
        tooltip.setAttribute("aria-hidden", "true");
    };
    cell.addEventListener("mouseenter", show);
    cell.addEventListener("mouseleave", hide);
    cell.addEventListener("focus", show);
    cell.addEventListener("blur", hide);
}
