import {
    openModal,
} from "../modals/modal.js";

import {
    openAddItemModal,
    openEditItemModal,
} from "../modals/items.js";

import {
    NutritionAPI,
} from "../api.js";

import {
    nutrition_t,
} from "../../i18n/index.js";

import type {
    Meal,
    MealItem,
} from "../types.js";


const ICONS = {
    pencil: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>
            <path d="m15 5 4 4"/>
        </svg>
    `,

    delete: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
        >
            <path d="M10 11v6"/>
            <path d="M14 11v6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
            <path d="M3 6h18"/>
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
    `,

    chevron: `
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <path d="m6 9 6 6 6-6"/>
        </svg>
    `,
};


type RefreshCallback =
    () => Promise<void> | void;

function formatMacro(value: number | null | undefined): string {
    return Number(value ?? 0).toFixed(1);
}

function formatCalories(value: number | null | undefined): string {
    return String(Math.round(Number(value ?? 0)));
}


function renderMealsSummary(meals: Meal[]): void {
    const element = document.getElementById("meals-day-summary");
    if (!element) return;

    const calories = meals.reduce(
        (sum, meal) => sum + Number(meal.total_calories ?? 0),
        0,
    );

    element.innerHTML = `
        <span class="meals-summary-value">${Math.round(calories)}</span>
        <span class="meals-summary-unit">${nutrition_t("units.kcal")}</span>
        <span class="meals-summary-divider"></span>
        <span class="meals-summary-count">${meals.length}</span>
    `;
}


export function renderMeals(
    meals: Meal[],
    onRefresh: RefreshCallback,
): void {
    const list =
        document.getElementById(
            "meals-list",
        );

    if (!list) {
        return;
    }

    list.innerHTML =
        "";

    renderMealsSummary(meals);

    if (!meals?.length) {
        const empty =
            document.createElement(
                "div",
            );

        empty.className =
            "meals-empty";

        empty.textContent =
            nutrition_t(
                "meals.emptyToday",
            );

        list.appendChild(
            empty,
        );

        return;
    }

    meals.forEach(
        (meal) => {
            list.appendChild(
                createMealCard(
                    meal,
                    onRefresh,
                ),
            );
        },
    );
}


function createMealCard(
    meal: Meal,
    onRefresh: RefreshCallback,
): HTMLElement {
    const card =
        document.createElement(
            "article",
        );

    card.className =
        "meal-card-large";

    const header =
        document.createElement(
            "div",
        );

    header.className =
        "meal-header-large";

    const content =
        document.createElement(
            "div",
        );

    content.className =
        "meal-content-large";

    content.appendChild(
        createMealItems(
            meal,
            onRefresh,
        ),
    );

    header.append(
        createMealInfo(
            meal,
            card,
            content,
        ),
        createMealActions(
            meal,
            onRefresh,
        ),
    );

    card.append(
        header,
        content,
    );

    return card;
}


function createMealInfo(
    meal: Meal,
    card: HTMLElement,
    content: HTMLElement,
): HTMLElement {
    const wrapper =
        document.createElement(
            "button",
        );

    wrapper.type =
        "button";

    wrapper.className =
        "meal-title-block";

    const titleRow =
        document.createElement(
            "div",
        );

    titleRow.className =
        "meal-title-row";

    const title =
        document.createElement(
            "span",
        );

    title.className =
        "meal-title";

    title.textContent =
        meal.name;

    const icon =
        document.createElement(
            "span",
        );

    icon.className =
        "meal-expand-icon";

    icon.innerHTML =
        ICONS.chevron;

    titleRow.append(
        title,
        icon,
    );

    const meta =
        document.createElement(
            "div",
        );

    meta.className =
        "meal-meta-large";

    meta.textContent = [
        `${formatCalories(meal.total_calories)} ${nutrition_t("units.kcal")}`,
        `${nutrition_t("units.proteinShort")} ${formatMacro(meal.total_protein)}`,
        `${nutrition_t("units.fatShort")} ${formatMacro(meal.total_fat)}`,
        `${nutrition_t("units.carbsShort")} ${formatMacro(meal.total_carbs)}`,
    ].join(" · ");

    wrapper.append(
        titleRow,
        meta,
    );

    wrapper.addEventListener(
        "click",
        () => {
            const isExpanded =
                card.classList.toggle(
                    "meal-expanded",
                );

            content.setAttribute(
                "aria-hidden",
                String(!isExpanded),
            );
        },
    );

    return wrapper;
}


function createMealActions(
    meal: Meal,
    onRefresh: RefreshCallback,
): HTMLElement {
    const actions =
        document.createElement(
            "div",
        );

    actions.className =
        "meal-actions-large";

    const addItem =
        document.createElement(
            "button",
        );

    addItem.type =
        "button";

    addItem.className =
        "meal-action-add";

    addItem.textContent =
        nutrition_t(
            "meals.addProduct",
        );

    addItem.addEventListener(
        "click",
        () => {
            openAddItemModal(
                meal.id,
            );
        },
    );

    const edit =
        createIconButton(
            "meal-action-icon",
            ICONS.pencil,
            nutrition_t(
                "actions.editMeal",
            ),
        );

    edit.addEventListener(
        "click",
        () => {
            const id =
                document.getElementById(
                    "edit-meal-id",
                ) as HTMLInputElement | null;

            const name =
                document.getElementById(
                    "edit-meal-name",
                ) as HTMLInputElement | null;

            const category =
                document.getElementById(
                    "edit-meal-category",
                ) as HTMLInputElement | null;

            const time =
                document.getElementById(
                    "edit-meal-time",
                ) as HTMLInputElement | null;

            if (
                !id
                || !name
                || !category
                || !time
            ) {
                return;
            }

            id.value =
                String(meal.id);

            name.value =
                meal.name || "";

            category.value =
                meal.category ||
                nutrition_t(
                    "meal.defaultCategory",
                );

            time.value =
                meal.time || "";

            openModal(
                "modal-edit-meal",
            );
        },
    );

    const remove =
        createIconButton(
            "meal-action-icon meal-action-delete",
            ICONS.delete,
            nutrition_t(
                "actions.deleteConfirm",
            ),
        );

    remove.addEventListener(
        "dblclick",
        async () => {
            await NutritionAPI.deleteMeal(
                meal.id,
            );

            await onRefresh();
        },
    );

    actions.append(
        addItem,
        edit,
        remove,
    );

    return actions;
}


function createMealItems(
    meal: Meal,
    onRefresh: RefreshCallback,
): HTMLElement {
    const container =
        document.createElement(
            "div",
        );

    container.className =
        "meal-items-large";

    if (!meal.items?.length) {
        const empty =
            document.createElement(
                "div",
            );

        empty.className =
            "meal-items-empty";

        empty.textContent =
            nutrition_t(
                "meals.noProducts",
            );

        container.appendChild(
            empty,
        );

        return container;
    }

    meal.items.forEach(
        (item) => {
            container.appendChild(
                createItemRow(
                    item,
                    onRefresh,
                ),
            );
        },
    );

    return container;
}


function createItemRow(
    item: MealItem,
    onRefresh: RefreshCallback,
): HTMLElement {
    const row =
        document.createElement(
            "div",
        );

    row.className =
        "meal-item-row-large";

    const info =
        document.createElement(
            "div",
        );

    info.className =
        "meal-item-info-large";

    const name =
        document.createElement(
            "div",
        );

    name.className =
        "meal-item-name-large";

    name.textContent =
        item.name;

    const macros =
        document.createElement(
            "div",
        );

    macros.className =
        "meal-item-macros-large";

    const amount =
        item.amount != null
            ? item.amount + " " + (item.unit ?? "g") + " · "
            : "";

    macros.textContent = amount + [
        `${formatCalories(item.calories)} ${nutrition_t("units.kcal")}`,
        `${nutrition_t("units.proteinShort")} ${formatMacro(item.protein)}`,
        `${nutrition_t("units.fatShort")} ${formatMacro(item.fat)}`,
        `${nutrition_t("units.carbsShort")} ${formatMacro(item.carbs)}`,
    ].join(" · ");

    info.append(
        name,
        macros,
    );

    const actions =
        document.createElement(
            "div",
        );

    actions.className =
        "meal-item-actions-large";

    const edit =
        createIconButton(
            "meal-item-action",
            ICONS.pencil,
            nutrition_t(
                "actions.editProduct",
            ),
        );

    edit.addEventListener(
        "click",
        () => {
            void openEditItemModal(
                item,
            );
        },
    );

    const remove =
        createIconButton(
            "meal-item-action meal-item-delete",
            ICONS.delete,
            nutrition_t(
                "actions.deleteConfirm",
            ),
        );

    remove.addEventListener(
        "dblclick",
        async () => {
            await NutritionAPI.deleteEntry(
                item.id,
            );

            await onRefresh();
        },
    );

    actions.append(
        edit,
        remove,
    );

    row.append(
        info,
        actions,
    );

    return row;
}


function createIconButton(
    className: string,
    icon: string,
    label: string,
): HTMLButtonElement {
    const button =
        document.createElement(
            "button",
        );

    button.type =
        "button";

    button.className =
        className;

    button.innerHTML =
        icon;

    button.setAttribute(
        "aria-label",
        label,
    );

    button.title =
        label;

    return button;
}