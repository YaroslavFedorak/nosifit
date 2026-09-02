import { el } from "../utils/dom.js";

function createCell(day) {
    const level = day && typeof day.level === "number" ? day.level : 0;
    const cell = el("div", { class: `dashboard-heatmap-cell dashboard-heatmap-cell--level-${level}`, role: "gridcell", "data-date": day ? day.date : "" }, [
        el("div", { class: "dashboard-heatmap-cell-inner" })
    ]);
    return cell;
}

export function renderHeatmap(container, data) {
    container.innerHTML = "";
    if (!data || !Array.isArray(data.days) || data.days.length === 0) {
        container.textContent = "Немає даних";
        return;
    }
    for (const d of data.days) {
        const cell = createCell(d);
        container.appendChild(cell);
    }
}
