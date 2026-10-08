/**
 * Meal list shared by the Nutrition page and the Dashboard widget.
 * Same markup and behaviour in both places; each page styles the density.
 */
import { NutritionAPI } from "../api.js";
import { formatAmount, mealCategoryLabel } from "../categories.js";
import { describeError } from "../errors.js";
import { openAddItemModal, openEditItemModal } from "../modals/items.js";
import { openEditMealModal } from "../modals/meals.js";
import { emitNutritionChange } from "../modals/modal.js";
import { nutrition_t } from "../../i18n/index.js";
import type { Meal, MealItem } from "../types.js";

type RefreshCallback = () => Promise<void> | void;

export interface MealListOptions {
    onRefresh: RefreshCallback;
    emptyText?: string;
}

const ICONS = {
    pencil: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/></svg>',
    trash: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
    plus: '<svg class="meal-action-add-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14"/><path d="M5 12h14"/></svg>',
    chevron: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',
};

const CONFIRM_TIMEOUT_MS = 3000;

// Which meals are expanded survives re-renders (e.g. after adding water).
const expandedMeals = new Set<number>();

function formatCalories(value: number | null | undefined): string {
    return String(Math.round(Number(value ?? 0)));
}

function formatMacro(value: number | null | undefined): string {
    const number = Number(value ?? 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

export function macrosLine(source: {
    calories?: number | null;
    protein?: number | null;
    fat?: number | null;
    carbs?: number | null;
}): string {
    return [
        `${formatCalories(source.calories)} ${nutrition_t("units.kcal")}`,
        `${nutrition_t("units.proteinShort")} ${formatMacro(source.protein)}`,
        `${nutrition_t("units.fatShort")} ${formatMacro(source.fat)}`,
        `${nutrition_t("units.carbsShort")} ${formatMacro(source.carbs)}`,
    ].join(" · ");
}

function createIconButton(className: string, icon: string, label: string): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.innerHTML = icon;
    button.setAttribute("aria-label", label);
    button.title = label;
    return button;
}

/**
 * Two-step delete: the first click arms the button, the second (within 3 s)
 * deletes. No accidental deletes, no browser confirm() dialog.
 */
function createDeleteButton(
    className: string,
    label: string,
    onConfirm: () => Promise<void>,
): HTMLButtonElement {
    const button = createIconButton(className, ICONS.trash, label);
    let timer: number | undefined;

    const disarm = (): void => {
        window.clearTimeout(timer);
        button.classList.remove("is-confirming");
        button.title = label;
        button.setAttribute("aria-label", label);
    };

    button.addEventListener("click", async (event) => {
        event.stopPropagation();

        if (!button.classList.contains("is-confirming")) {
            button.classList.add("is-confirming");
            const confirmLabel = nutrition_t("actions.confirmDelete");
            button.title = confirmLabel;
            button.setAttribute("aria-label", confirmLabel);
            timer = window.setTimeout(disarm, CONFIRM_TIMEOUT_MS);
            return;
        }

        disarm();
        button.disabled = true;

        try {
            await onConfirm();
        } catch (error) {
            button.disabled = false;
            button.title = describeError(error);
        }
    });

    button.addEventListener("blur", disarm);
    return button;
}

function createItemRow(item: MealItem, options: MealListOptions): HTMLElement {
    const row = document.createElement("div");
    row.className = "meal-item-row-large";

    const info = document.createElement("div");
    info.className = "meal-item-info-large";

    const name = document.createElement("div");
    name.className = "meal-item-name-large";
    name.textContent = item.name;

    const macros = document.createElement("div");
    macros.className = "meal-item-macros-large";
    macros.textContent = `${formatAmount(item.amount ?? item.weight, item.unit)} · ${macrosLine(item)}`;

    info.append(name, macros);

    const actions = document.createElement("div");
    actions.className = "meal-item-actions-large";

    const edit = createIconButton("meal-item-action", ICONS.pencil, nutrition_t("actions.editProduct"));
    edit.addEventListener("click", () => void openEditItemModal(item));

    const remove = createDeleteButton(
        "meal-item-action meal-item-delete",
        nutrition_t("actions.deleteProduct"),
        async () => {
            await NutritionAPI.deleteEntry(item.id);
            emitNutritionChange("meals");
            await options.onRefresh();
        },
    );

    actions.append(edit, remove);
    row.append(info, actions);
    return row;
}

function createMealCard(meal: Meal, options: MealListOptions): HTMLElement {
    const card = document.createElement("article");
    card.className = "meal-card-large";
    card.dataset.mealId = String(meal.id);

    const header = document.createElement("div");
    header.className = "meal-header-large";

    const content = document.createElement("div");
    content.className = "meal-content-large";
    content.id = `meal-content-${meal.id}`;

    /* Title block (toggles the product list) */
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "meal-title-block";
    toggle.setAttribute("aria-controls", content.id);

    const titleRow = document.createElement("div");
    titleRow.className = "meal-title-row";

    const title = document.createElement("span");
    title.className = "meal-title";
    title.textContent = mealCategoryLabel(meal.category ?? meal.name);

    titleRow.appendChild(title);

    if (meal.time) {
        const time = document.createElement("span");
        time.className = "meal-time";
        time.textContent = meal.time;
        titleRow.appendChild(time);
    }

    const chevron = document.createElement("span");
    chevron.className = "meal-expand-icon";
    chevron.innerHTML = ICONS.chevron;
    titleRow.appendChild(chevron);

    const meta = document.createElement("div");
    meta.className = "meal-meta-large";
    meta.textContent = macrosLine({
        calories: meal.total_calories,
        protein: meal.total_protein,
        fat: meal.total_fat,
        carbs: meal.total_carbs,
    });

    toggle.append(titleRow, meta);

    const setExpanded = (expanded: boolean): void => {
        card.classList.toggle("meal-expanded", expanded);
        toggle.setAttribute("aria-expanded", String(expanded));
        content.setAttribute("aria-hidden", String(!expanded));
        if (expanded) expandedMeals.add(meal.id);
        else expandedMeals.delete(meal.id);
    };

    toggle.addEventListener("click", () => setExpanded(!card.classList.contains("meal-expanded")));

    /* Actions */
    const actions = document.createElement("div");
    actions.className = "meal-actions-large";

    const addLabel = nutrition_t("meals.addProduct").replace(/^\+\s*/, "");
    const add = document.createElement("button");
    add.type = "button";
    add.className = "meal-action-add";
    add.title = nutrition_t("items.addTitle");
    add.setAttribute("aria-label", nutrition_t("items.addTitle"));
    add.innerHTML = ICONS.plus;
    const addText = document.createElement("span");
    addText.className = "meal-action-add-label";
    addText.textContent = addLabel;
    add.appendChild(addText);
    add.addEventListener("click", () => openAddItemModal(meal.id, meal));

    const edit = createIconButton("meal-action-icon", ICONS.pencil, nutrition_t("actions.editMeal"));
    edit.addEventListener("click", () => openEditMealModal(meal));

    const remove = createDeleteButton(
        "meal-action-icon meal-action-delete",
        nutrition_t("actions.deleteMeal"),
        async () => {
            await NutritionAPI.deleteMeal(meal.id);
            expandedMeals.delete(meal.id);
            emitNutritionChange("meals");
            await options.onRefresh();
        },
    );

    actions.append(add, edit, remove);
    header.append(toggle, actions);

    /* Products */
    const items = document.createElement("div");
    items.className = "meal-items-large";

    if (!meal.items?.length) {
        const empty = document.createElement("div");
        empty.className = "meal-items-empty";
        empty.textContent = nutrition_t("meals.noProducts");
        items.appendChild(empty);
    } else {
        meal.items.forEach((item) => items.appendChild(createItemRow(item, options)));
    }

    content.appendChild(items);
    card.append(header, content);
    setExpanded(expandedMeals.has(meal.id));
    return card;
}

export function renderMealList(
    container: HTMLElement,
    meals: Meal[],
    options: MealListOptions,
): void {
    container.innerHTML = "";

    if (!meals?.length) {
        const empty = document.createElement("div");
        empty.className = "meals-empty";
        empty.textContent = options.emptyText ?? nutrition_t("meals.emptyToday");
        container.appendChild(empty);
        return;
    }

    meals.forEach((meal) => container.appendChild(createMealCard(meal, options)));
}
