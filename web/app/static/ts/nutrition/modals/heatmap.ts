import {
    NutritionAPI,
} from "../api.js";

import type {
    Meal,
    NutritionDayDetails,
    NutritionHeatmapDay,
} from "../types.js";


let calendarModal:
    HTMLDivElement | null = null;

let dayModal:
    HTMLDivElement | null = null;


let calendarYear =
    new Date().getFullYear();

let calendarDays:
    NutritionHeatmapDay[] = [];


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


function formatNumber(
    value: number,
): string {
    return Number.isInteger(value)
        ? String(value)
        : value.toFixed(1);
}


function closeModal(
    modal: HTMLElement | null,
): void {
    if (!modal) {
        return;
    }

    modal.classList.remove(
        "open",
    );

    modal.setAttribute(
        "aria-hidden",
        "true",
    );
}


function openModal(
    modal: HTMLElement | null,
): void {
    if (!modal) {
        return;
    }

    modal.classList.add(
        "open",
    );

    modal.setAttribute(
        "aria-hidden",
        "false",
    );
}


function renderCalendar(): void {
    const grid =
        document.getElementById(
            "nutrition-calendar-grid",
        );

    if (!grid) {
        return;
    }

    grid.innerHTML =
        "";

    const year =
        calendarYear;

    const firstDate =
        new Date(
            year,
            0,
            1,
            12,
        );

    const lastDate =
        new Date(
            year,
            11,
            31,
            12,
        );

    const firstWeekday =
        firstDate.getDay() === 0
            ? 6
            : firstDate.getDay() - 1;

    for (
        let index = 0;
        index < firstWeekday;
        index += 1
    ) {
        const empty =
            document.createElement(
                "div",
            );

        empty.className =
            "nutrition-calendar-empty";

        empty.setAttribute(
            "aria-hidden",
            "true",
        );

        grid.appendChild(
            empty,
        );
    }

    const dayMap =
        new Map(
            calendarDays.map(
                (day) => [
                    day.date,
                    day,
                ],
            ),
        );

    for (
        let date = new Date(firstDate);
        date <= lastDate;
        date.setDate(
            date.getDate() + 1,
        )
    ) {
        const dateKey =
            [
                date.getFullYear(),
                String(
                    date.getMonth() + 1,
                ).padStart(
                    2,
                    "0",
                ),
                String(
                    date.getDate(),
                ).padStart(
                    2,
                    "0",
                ),
            ].join("-");

        const data =
            dayMap.get(
                dateKey,
            );

        const item =
            document.createElement(
                "button",
            );

        item.type =
            "button";

        item.className =
            "nutrition-calendar-item";

        if (data) {
            item.dataset.level =
                String(
                    data.level,
                );

            if (data.is_today) {
                item.classList.add(
                    "today",
                );
            }

            item.innerHTML = `
                <span class="nutrition-calendar-date">
                    ${date.getDate()}
                </span>

                <span class="nutrition-calendar-load">
                    ${data.kcal} ккал
                </span>
            `;

            item.addEventListener(
                "click",
                () => {
                    void openDayDetails(
                        dateKey,
                    );
                },
            );

        } else {
            item.disabled =
                true;

            item.setAttribute(
                "aria-label",
                `${date.getDate()} число, немає даних`,
            );

            item.innerHTML = `
                <span class="nutrition-calendar-date">
                    ${date.getDate()}
                </span>
            `;
        }

        grid.appendChild(
            item,
        );
    }

    const yearLabel =
        document.getElementById(
            "nutrition-calendar-current-year",
        );

    if (yearLabel) {
        yearLabel.textContent =
            String(
                year,
            );
    }

    const title =
        document.getElementById(
            "nutrition-calendar-year",
        );

    if (title) {
        title.textContent =
            String(
                year,
            );
    }
}


function renderStats(
    data: NutritionDayDetails,
): void {
    const container =
        document.getElementById(
            "nutrition-day-stats",
        );

    if (!container) {
        return;
    }

    const caloriePercent =
        data.calorie_goal > 0
            ? Math.round(
                data.calories /
                data.calorie_goal *
                100,
            )
            : 0;

    container.innerHTML = `
        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Калорії
            </span>

            <strong>
                ${formatNumber(data.calories)}
                <small>
                    / ${formatNumber(data.calorie_goal)} ккал
                </small>
            </strong>

            <span class="nutrition-day-stat-meta">
                ${caloriePercent}%
            </span>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Білки
            </span>

            <strong>
                ${formatNumber(data.protein)}
                <small>
                    / ${formatNumber(data.protein_goal)} г
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Жири
            </span>

            <strong>
                ${formatNumber(data.fat)}
                <small>
                    / ${formatNumber(data.fat_goal)} г
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Вуглеводи
            </span>

            <strong>
                ${formatNumber(data.carbs)}
                <small>
                    / ${formatNumber(data.carbs_goal)} г
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Вода
            </span>

            <strong>
                ${formatNumber(data.water)}
                <small>
                    / ${formatNumber(data.water_goal)} л
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                Вага
            </span>

            <strong>
                ${
                    data.current_weight !== null
                        ? `${formatNumber(data.current_weight)} кг`
                        : "—"
                }
            </strong>

        </div>
    `;
}


function renderMeal(
    meal: Meal,
): HTMLDivElement {
    const element =
        document.createElement(
            "div",
        );

    element.className =
        "nutrition-day-meal";

    const items =
        meal.items || [];

    const itemsHtml =
        items.length
            ? items.map(
                (item) => `
                    <div class="nutrition-day-food">

                        <div>

                            <span class="nutrition-day-food-name">
                                ${item.name}
                            </span>

                            ${
                                item.weight !== null &&
                                item.weight !== undefined
                                    ? `
                                        <span class="nutrition-day-food-weight">
                                            ${formatNumber(item.weight)} г
                                        </span>
                                    `
                                    : ""
                            }

                        </div>

                        <span class="nutrition-day-food-kcal">
                            ${item.calories} ккал
                        </span>

                    </div>
                `,
            ).join("")
            : `
                <div class="nutrition-day-empty-items">
                    Немає доданих продуктів
                </div>
            `;

    element.innerHTML = `
        <div class="nutrition-day-meal-header">

            <div>

                <div class="nutrition-day-meal-name">
                    ${meal.name}
                </div>

                <div class="nutrition-day-meal-meta">
                    ${
                        meal.category ||
                        "Прийом їжі"
                    }

                    ${
                        meal.time
                            ? ` · ${meal.time}`
                            : ""
                    }
                </div>

            </div>

            <div class="nutrition-day-meal-kcal">
                ${meal.total_calories || 0} ккал
            </div>

        </div>


        <div class="nutrition-day-foods">
            ${itemsHtml}
        </div>
    `;

    return element;
}


function renderMeals(
    data: NutritionDayDetails,
): void {
    const container =
        document.getElementById(
            "nutrition-day-meals",
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        "";

    if (!data.meals.length) {
        container.innerHTML = `
            <div class="nutrition-day-no-meals">

                <strong>
                    Немає прийомів їжі
                </strong>

                <span>
                    Цього дня харчування ще не записано.
                </span>

            </div>
        `;

        return;
    }

    const title =
        document.createElement(
            "div",
        );

    title.className =
        "nutrition-day-section-title";

    title.textContent =
        "Прийоми їжі";

    container.appendChild(
        title,
    );

    data.meals.forEach(
        (meal) => {
            container.appendChild(
                renderMeal(
                    meal,
                ),
            );
        },
    );
}


async function openDayDetails(
    date: string,
): Promise<void> {
    if (!dayModal) {
        return;
    }

    const title =
        document.getElementById(
            "nutrition-day-title",
        );

    const subtitle =
        document.getElementById(
            "nutrition-day-subtitle",
        );

    const stats =
        document.getElementById(
            "nutrition-day-stats",
        );

    const meals =
        document.getElementById(
            "nutrition-day-meals",
        );

    if (title) {
        title.textContent =
            formatDate(
                date,
            );
    }

    if (subtitle) {
        subtitle.textContent =
            "Завантаження даних...";
    }

    if (stats) {
        stats.innerHTML =
            "";
    }

    if (meals) {
        meals.innerHTML =
            "";
    }

    closeModal(
        calendarModal,
    );

    openModal(
        dayModal,
    );

    try {
        const data =
            await NutritionAPI.getDayDetails(
                date,
            );

        if (subtitle) {
            subtitle.textContent =
                `${data.meals.length} прийомів їжі`;
        }

        renderStats(
            data,
        );

        renderMeals(
            data,
        );

    } catch (error) {
        console.error(
            "Failed to load nutrition day:",
            error,
        );

        if (subtitle) {
            subtitle.textContent =
                "Не вдалося завантажити дані";
        }
    }
}


async function loadCalendarYear(
    year: number,
): Promise<void> {
    const grid =
        document.getElementById(
            "nutrition-calendar-grid",
        );

    if (grid) {
        grid.setAttribute(
            "aria-busy",
            "true",
        );
    }

    try {
        const data =
            await NutritionAPI.getHeatmap(
                year,
            );

        calendarYear =
            data.year;

        calendarDays =
            data.days;

        renderCalendar();

    } catch (error) {
        console.error(
            "Failed to load nutrition calendar:",
            error,
        );

    } finally {
        if (grid) {
            grid.setAttribute(
                "aria-busy",
                "false",
            );
        }
    }
}


function setupEvents(): void {
    document.addEventListener(
        "nutrition:open-calendar",
        (
            event: Event,
        ) => {
            const customEvent =
                event as CustomEvent<{
                    year: number;
                    days: NutritionHeatmapDay[];
                }>;

            calendarYear =
                customEvent.detail.year;

            calendarDays =
                customEvent.detail.days;

            renderCalendar();

            openModal(
                calendarModal,
            );
        },
    );


    document.addEventListener(
        "nutrition:open-day",
        (
            event: Event,
        ) => {
            const customEvent =
                event as CustomEvent<{
                    date: string;
                }>;

            void openDayDetails(
                customEvent.detail.date,
            );
        },
    );


    document.addEventListener(
        "click",
        (
            event: Event,
        ) => {
            const target =
                event.target as HTMLElement;

            if (
                target.closest(
                    "[data-close-calendar]",
                )
            ) {
                closeModal(
                    calendarModal,
                );
            }

            if (
                target.closest(
                    "[data-close-day]",
                )
            ) {
                closeModal(
                    dayModal,
                );
            }

            if (
                target === calendarModal
            ) {
                closeModal(
                    calendarModal,
                );
            }

            if (
                target === dayModal
            ) {
                closeModal(
                    dayModal,
                );
            }
        },
    );


    document.addEventListener(
        "keydown",
        (
            event: KeyboardEvent,
        ) => {
            if (
                event.key !== "Escape"
            ) {
                return;
            }

            closeModal(
                calendarModal,
            );

            closeModal(
                dayModal,
            );
        },
    );


    document.getElementById(
        "nutrition-calendar-prev",
    )?.addEventListener(
        "click",
        () => {
            calendarYear -= 1;

            void loadCalendarYear(
                calendarYear,
            );
        },
    );


    document.getElementById(
        "nutrition-calendar-next",
    )?.addEventListener(
        "click",
        () => {
            calendarYear += 1;

            void loadCalendarYear(
                calendarYear,
            );
        },
    );
}


export function setupNutritionHeatmapModals(): void {
    calendarModal =
        document.getElementById(
            "nutrition-calendar-modal",
        ) as HTMLDivElement | null;

    dayModal =
        document.getElementById(
            "nutrition-day-modal",
        ) as HTMLDivElement | null;

    if (
        !calendarModal ||
        !dayModal
    ) {
        console.error(
            "Nutrition heatmap modals were not found in the DOM.",
        );

        return;
    }

    setupEvents();
}