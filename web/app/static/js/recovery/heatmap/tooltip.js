import { formatTooltipDayHTML } from "./formatters.js";

export function attachTooltip(cell, data) {
  if (!cell) return;

  let localTooltip = cell.querySelector(".rc-heatmap-tooltip");
  if (!localTooltip) {
    localTooltip = document.createElement("div");
    localTooltip.className = "rc-heatmap-tooltip";
    localTooltip.setAttribute("role", "tooltip");
    localTooltip.setAttribute("aria-hidden", "true");
    cell.appendChild(localTooltip);
  }

  function renderContent(d) {
    const payload = {
      date: d?.date || null,
      recovery_score: d?.recovery_score != null ? d.recovery_score : 0
    };
    localTooltip.innerHTML = formatTooltipDayHTML(payload);
  }

  function show() {
    renderContent(data);
    localTooltip.classList.add("visible");
    localTooltip.setAttribute("aria-hidden", "false");
  }

  function hide() {
    localTooltip.classList.remove("visible");
    localTooltip.setAttribute("aria-hidden", "true");
  }

  cell.addEventListener("mouseenter", show);
  cell.addEventListener("mouseleave", hide);
  cell.addEventListener("focus", show);
  cell.addEventListener("blur", hide);
}
