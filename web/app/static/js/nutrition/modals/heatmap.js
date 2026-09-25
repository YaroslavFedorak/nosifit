import { NutritionAPI, } from "../api.js";
import { getLocale, nutrition_t, } from "../../i18n/index.js";
let calendarModal = null;
let dayModal = null;
let calendarYear = new Date().getFullYear();
let calendarDays = [];
function formatDate(dateString) {
    const date = new Date(`${dateString}T12:00:00`);
    return date.toLocaleDateString(getLocale(), {
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}
function formatNumber(value) {
    return Number.isInteger(value)
        ? String(value)
        : value.toFixed(1);
}
function closeModal(modal) {
    if (!modal) {
        return;
    }
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}
function openModal(modal) {
    if (!modal) {
        return;
    }
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}
function renderCalendar() {
    const grid = document.getElementById("nutrition-calendar-grid");
    if (!grid) {
        return;
    }
    grid.innerHTML =
        "";
    const year = calendarYear;
    const firstDate = new Date(year, 0, 1, 12);
    const lastDate = new Date(year, 11, 31, 12);
    const firstWeekday = firstDate.getDay() === 0
        ? 6
        : firstDate.getDay() - 1;
    for (let index = 0; index < firstWeekday; index += 1) {
        const empty = document.createElement("div");
        empty.className =
            "nutrition-calendar-empty";
        empty.setAttribute("aria-hidden", "true");
        grid.appendChild(empty);
    }
    const dayMap = new Map(calendarDays.map((day) => [
        day.date,
        day,
    ]));
    for (let date = new Date(firstDate); date <= lastDate; date.setDate(date.getDate() + 1)) {
        const dateKey = [
            date.getFullYear(),
            String(date.getMonth() + 1).padStart(2, "0"),
            String(date.getDate()).padStart(2, "0"),
        ].join("-");
        const data = dayMap.get(dateKey);
        const item = document.createElement("button");
        item.type =
            "button";
        item.className =
            "nutrition-calendar-item";
        if (data) {
            item.dataset.level =
                String(data.level);
            if (data.is_today) {
                item.classList.add("today");
            }
            item.innerHTML = `
                <span class="nutrition-calendar-date">
                    ${date.getDate()}
                </span>

                <span class="nutrition-calendar-load">
                    ${data.kcal} ${nutrition_t("units.kcal")}
                </span>
            `;
            item.addEventListener("click", () => {
                void openDayDetails(dateKey);
            });
        }
        else {
            item.disabled =
                true;
            item.setAttribute("aria-label", nutrition_t("calendar.noData", {
                day: date.getDate(),
            }));
            item.innerHTML = `
                <span class="nutrition-calendar-date">
                    ${date.getDate()}
                </span>
            `;
        }
        grid.appendChild(item);
    }
    const yearLabel = document.getElementById("nutrition-calendar-current-year");
    if (yearLabel) {
        yearLabel.textContent =
            String(year);
    }
    const title = document.getElementById("nutrition-calendar-year");
    if (title) {
        title.textContent =
            String(year);
    }
}
function renderStats(data) {
    const container = document.getElementById("nutrition-day-stats");
    if (!container) {
        return;
    }
    const caloriePercent = data.calorie_goal > 0
        ? Math.round(data.calories /
            data.calorie_goal *
            100)
        : 0;
    container.innerHTML = `
        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.calories")}
            </span>

            <strong>
                ${formatNumber(data.calories)}
                <small>
                    / ${formatNumber(data.calorie_goal)} ${nutrition_t("units.kcal")}
                </small>
            </strong>

            <span class="nutrition-day-stat-meta">
                ${caloriePercent}%
            </span>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.protein")}
            </span>

            <strong>
                ${formatNumber(data.protein)}
                <small>
                    / ${formatNumber(data.protein_goal)} ${nutrition_t("units.grams")}
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.fat")}
            </span>

            <strong>
                ${formatNumber(data.fat)}
                <small>
                    / ${formatNumber(data.fat_goal)} ${nutrition_t("units.grams")}
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.carbs")}
            </span>

            <strong>
                ${formatNumber(data.carbs)}
                <small>
                    / ${formatNumber(data.carbs_goal)} ${nutrition_t("units.grams")}
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.water")}
            </span>

            <strong>
                ${formatNumber(data.water)}
                <small>
                    / ${formatNumber(data.water_goal)} ${nutrition_t("units.liters")}
                </small>
            </strong>

        </div>


        <div class="nutrition-day-stat">

            <span class="nutrition-day-stat-label">
                ${nutrition_t("stats.weight")}
            </span>

            <strong>
                ${data.current_weight !== null
        ? `${formatNumber(data.current_weight)} ${nutrition_t("units.kg")}`
        : "—"}
            </strong>

        </div>
    `;
}
function renderMeal(meal) {
    const element = document.createElement("div");
    element.className =
        "nutrition-day-meal";
    const items = meal.items || [];
    const itemsHtml = items.length
        ? items.map((item) => `
                    <div class="nutrition-day-food">

                        <div>

                            <span class="nutrition-day-food-name">
                                ${item.name}
                            </span>

                            ${item.weight !== null &&
            item.weight !== undefined
            ? `
                                        <span class="nutrition-day-food-weight">
                                            ${formatNumber(item.weight)} ${nutrition_t("units.grams")}
                                        </span>
                                    `
            : ""}

                        </div>

                        <span class="nutrition-day-food-kcal">
                            ${item.calories} ${nutrition_t("units.kcal")}
                        </span>

                    </div>
                `).join("")
        : `
                <div class="nutrition-day-empty-items">
                    ${nutrition_t("dayDetails.noProducts")}
                </div>
            `;
    element.innerHTML = `
        <div class="nutrition-day-meal-header">

            <div>

                <div class="nutrition-day-meal-name">
                    ${meal.name}
                </div>

                <div class="nutrition-day-meal-meta">
                    ${meal.category ||
        nutrition_t("meal.defaultCategory")}

                    ${meal.time
        ? ` · ${meal.time}`
        : ""}

                </div>

            </div>

            <div class="nutrition-day-meal-kcal">
                ${meal.total_calories || 0} ${nutrition_t("units.kcal")}
            </div>

        </div>


        <div class="nutrition-day-foods">
            ${itemsHtml}
        </div>
    `;
    return element;
}
function renderMeals(data) {
    const container = document.getElementById("nutrition-day-meals");
    if (!container) {
        return;
    }
    container.innerHTML =
        "";
    if (!data.meals.length) {
        container.innerHTML = `
            <div class="nutrition-day-no-meals">

                <strong>
                    ${nutrition_t("dayDetails.noMeals")}
                </strong>

                <span>
                    ${nutrition_t("dayDetails.noMealsDescription")}
                </span>

            </div>
        `;
        return;
    }
    const title = document.createElement("div");
    title.className =
        "nutrition-day-section-title";
    title.textContent =
        nutrition_t("dayDetails.mealsTitle");
    container.appendChild(title);
    data.meals.forEach((meal) => {
        container.appendChild(renderMeal(meal));
    });
}
async function openDayDetails(date) {
    if (!dayModal) {
        return;
    }
    const title = document.getElementById("nutrition-day-title");
    const subtitle = document.getElementById("nutrition-day-subtitle");
    const stats = document.getElementById("nutrition-day-stats");
    const meals = document.getElementById("nutrition-day-meals");
    if (title) {
        title.textContent =
            formatDate(date);
    }
    if (subtitle) {
        subtitle.textContent =
            nutrition_t("dayDetails.loading");
    }
    if (stats) {
        stats.innerHTML =
            "";
    }
    if (meals) {
        meals.innerHTML =
            "";
    }
    closeModal(calendarModal);
    openModal(dayModal);
    try {
        const data = await NutritionAPI.getDayDetails(date);
        if (subtitle) {
            subtitle.textContent =
                nutrition_t("dayDetails.mealsCount", {
                    count: data.meals.length,
                });
        }
        renderStats(data);
        renderMeals(data);
    }
    catch (error) {
        console.error("Failed to load nutrition day:", error);
        if (subtitle) {
            subtitle.textContent =
                nutrition_t("dayDetails.loadError");
        }
    }
}
async function loadCalendarYear(year) {
    const grid = document.getElementById("nutrition-calendar-grid");
    if (grid) {
        grid.setAttribute("aria-busy", "true");
    }
    try {
        const data = await NutritionAPI.getHeatmap(year);
        calendarYear =
            data.year;
        calendarDays =
            data.days;
        renderCalendar();
    }
    catch (error) {
        console.error("Failed to load nutrition calendar:", error);
    }
    finally {
        if (grid) {
            grid.setAttribute("aria-busy", "false");
        }
    }
}
function setupEvents() {
    document.addEventListener("nutrition:open-calendar", (event) => {
        const customEvent = event;
        calendarYear =
            customEvent.detail.year;
        calendarDays =
            customEvent.detail.days;
        renderCalendar();
        openModal(calendarModal);
    });
    document.addEventListener("nutrition:open-day", (event) => {
        const customEvent = event;
        void openDayDetails(customEvent.detail.date);
    });
    document.addEventListener("click", (event) => {
        const target = event.target;
        if (target.closest("[data-close-calendar]")) {
            closeModal(calendarModal);
        }
        if (target.closest("[data-close-day]")) {
            closeModal(dayModal);
        }
        if (target === calendarModal) {
            closeModal(calendarModal);
        }
        if (target === dayModal) {
            closeModal(dayModal);
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        closeModal(calendarModal);
        closeModal(dayModal);
    });
    document.getElementById("nutrition-calendar-prev")?.addEventListener("click", () => {
        calendarYear -= 1;
        void loadCalendarYear(calendarYear);
    });
    document.getElementById("nutrition-calendar-next")?.addEventListener("click", () => {
        calendarYear += 1;
        void loadCalendarYear(calendarYear);
    });
}
export function setupNutritionHeatmapModals() {
    calendarModal =
        document.getElementById("nutrition-calendar-modal");
    dayModal =
        document.getElementById("nutrition-day-modal");
    if (!calendarModal ||
        !dayModal) {
        console.error("Nutrition heatmap modals were not found in the DOM.");
        return;
    }
    setupEvents();
}
