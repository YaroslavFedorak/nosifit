import {
    NutritionAPI,
} from "./api.js";

import type {
    NutritionHeatmapDay,
} from "./types.js";


const MONTHS = [
    "Січ",
    "Лют",
    "Бер",
    "Кві",
    "Тра",
    "Чер",
    "Лип",
    "Сер",
    "Вер",
    "Жов",
    "Лис",
    "Гру",
];


let currentYear =
    new Date().getFullYear();

let currentDays: NutritionHeatmapDay[] = [];


function formatDate(
    dateString: string,
): string {
    const date =
        new Date(
            `${dateString}T12:00:00`,
        );

    return date.toLocaleDateString(
        "uk-UA",
        {
            day: "numeric",
            month: "long",
            year: "numeric",
        },
    );
}


function getMondayIndex(
    dateString: string,
): number {
    const date =
        new Date(
            `${dateString}T12:00:00`,
        );

    const day =
        date.getDay();

    return day === 0
        ? 6
        : day - 1;
}


function createTooltip(
    day: NutritionHeatmapDay,
): HTMLDivElement {
    const tooltip =
        document.createElement("div");

    tooltip.className =
        "nutrition-heatmap-tooltip";

    const date =
        document.createElement("strong");

    date.textContent =
        formatDate(
            day.date,
        );

    const kcal =
        document.createElement("span");

    kcal.textContent =
        `${day.kcal} ккал`;

    const macros =
        document.createElement("span");

    macros.textContent =
        `Б ${day.protein} г · Ж ${day.fat} г · В ${day.carbs} г`;

    tooltip.append(
        date,
        kcal,
        macros,
    );

    return tooltip;
}


function createCell(
    day: NutritionHeatmapDay,
): HTMLButtonElement {
    const cell =
        document.createElement("button");

    cell.type =
        "button";

    cell.className =
        "nutrition-heatmap-cell";

    cell.dataset.level =
        String(day.level);

    cell.dataset.date =
        day.date;

    if (day.is_today) {
        cell.classList.add(
            "today",
        );
    }

    cell.setAttribute(
        "aria-label",
        `${formatDate(day.date)}, ${day.kcal} ккал`,
    );

    cell.appendChild(
        createTooltip(day),
    );

    cell.addEventListener(
        "click",
        () => {
            document.dispatchEvent(
                new CustomEvent(
                    "nutrition:open-day",
                    {
                        detail: {
                            date: day.date,
                        },
                    },
                ),
            );
        },
    );

    return cell;
}


function createEmptyCell(): HTMLDivElement {
    const cell =
        document.createElement("div");

    cell.className =
        "nutrition-heatmap-cell nutrition-heatmap-cell-empty";

    cell.setAttribute(
        "aria-hidden",
        "true",
    );

    return cell;
}


function renderMonths(
    days: NutritionHeatmapDay[],
): void {
    const months =
        document.getElementById(
            "nutrition-heatmap-months",
        );

    if (!months) {
        return;
    }

    months.innerHTML =
        "";

    let lastMonth =
        -1;

    days.forEach(
        (day) => {
            const date =
                new Date(
                    `${day.date}T12:00:00`,
                );

            const month =
                date.getMonth();

            if (month === lastMonth) {
                return;
            }

            lastMonth =
                month;

            const element =
                document.createElement(
                    "span",
                );

            element.textContent =
                MONTHS[month];

            element.dataset.month =
                String(month);

            months.appendChild(
                element,
            );
        },
    );
}


function renderHeatmap(
    days: NutritionHeatmapDay[],
): void {
    const grid =
        document.getElementById(
            "nutrition-heatmap-grid",
        );

    if (!grid) {
        return;
    }

    grid.innerHTML =
        "";

    if (!days.length) {
        renderMonths(
            [],
        );

        return;
    }

    const firstDay =
        days[0];

    const offset =
        getMondayIndex(
            firstDay.date,
        );

    for (
        let index = 0;
        index < offset;
        index += 1
    ) {
        grid.appendChild(
            createEmptyCell(),
        );
    }

    days.forEach(
        (day) => {
            grid.appendChild(
                createCell(
                    day,
                ),
            );
        },
    );

    renderMonths(
        days,
    );
}


function updateYearSelect(): void {
    const select =
        document.getElementById(
            "heatmap-year",
        ) as HTMLSelectElement | null;

    if (!select) {
        return;
    }

    select.value =
        String(currentYear);
}


async function loadHeatmap(
    year: number,
): Promise<void> {
    const widget =
        document.getElementById(
            "nutrition-heatmap-widget",
        );

    if (!widget) {
        return;
    }

    widget.classList.add(
        "is-loading",
    );

    try {
        const data =
            await NutritionAPI.getHeatmap(
                year,
            );

        currentYear =
            data.year;

        currentDays =
            data.days;

        renderHeatmap(
            data.days,
        );

        updateYearSelect();

    } catch (error) {
        console.error(
            "Failed to load nutrition heatmap:",
            error,
        );

    } finally {
        widget.classList.remove(
            "is-loading",
        );
    }
}


function setupYearSelect(): void {
    const select =
        document.getElementById(
            "heatmap-year",
        ) as HTMLSelectElement | null;

    if (!select) {
        return;
    }

    select.addEventListener(
        "change",
        () => {
            const year =
                Number(
                    select.value,
                );

            if (!Number.isFinite(year)) {
                return;
            }

            currentYear =
                year;

            void loadHeatmap(
                currentYear,
            );
        },
    );
}


function setupCalendarButton(): void {
    const button =
        document.getElementById(
            "open-nutrition-calendar",
        );

    if (!button) {
        return;
    }

    button.addEventListener(
        "click",
        () => {
            document.dispatchEvent(
                new CustomEvent(
                    "nutrition:open-calendar",
                    {
                        detail: {
                            year: currentYear,
                            days: currentDays,
                        },
                    },
                ),
            );
        },
    );
}


function setupExternalReload(): void {
    document.addEventListener(
        "nutrition:heatmap-reload",
        () => {
            void loadHeatmap(
                currentYear,
            );
        },
    );
}


export function initializeNutritionHeatmap(): void {
    setupYearSelect();
    setupCalendarButton();
    setupExternalReload();

    currentYear =
        new Date().getFullYear();

    void loadHeatmap(
        currentYear,
    );
}


export function getNutritionHeatmapDays(): NutritionHeatmapDay[] {
    return currentDays;
}


export function getNutritionHeatmapYear(): number {
    return currentYear;
}