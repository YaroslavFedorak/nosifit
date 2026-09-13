import { el } from "../utils/dom.js";

interface HeatmapDay {
    level?: number;
    date?: string;
}

interface HeatmapData {
    days?: HeatmapDay[];
}

function createCell(
    day: HeatmapDay | null | undefined
): HTMLElement {
    const level =
        day &&
        typeof day.level === "number"
            ? day.level
            : 0;

    return el(
        "div",
        {
            class:
                `dashboard-heatmap-cell dashboard-heatmap-cell--level-${level}`,
            role: "gridcell",
            "data-date":
                day?.date || ""
        },
        [
            el("div", {
                class:
                    "dashboard-heatmap-cell-inner"
            })
        ]
    );
}

export function renderHeatmap(
    container: HTMLElement,
    data: HeatmapData | null
): void {
    container.innerHTML = "";

    if (
        !data ||
        !Array.isArray(data.days) ||
        data.days.length === 0
    ) {
        container.textContent =
            "Немає даних";

        return;
    }

    for (const day of data.days) {
        container.appendChild(
            createCell(day)
        );
    }
}