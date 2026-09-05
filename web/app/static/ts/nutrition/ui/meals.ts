import {
    openModal,
} from "../modals/modal.js";

import {
    NutritionAPI,
} from "../api.js";

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

type RefreshCallback = () => Promise<void> | void;

export function renderMeals(
    meals: Meal[],
    onRefresh: RefreshCallback,
): void {
    const list = document.getElementById(
        "meals-list",
    );

    if (!list) {
        return;
    }

    list.innerHTML = "";

    if (!meals?.length) {
        const empty = document.createElement("div");

        empty.className = "meals-empty";

        empty.textContent =
            "Ще немає прийомів за сьогодні.";

        list.appendChild(empty);

        return;
    }

    meals.forEach((meal) => {
        list.appendChild(
            createMealCard(
                meal,
                onRefresh,
            ),
        );
    });
}

function createMealCard(
    meal: Meal,
    onRefresh: RefreshCallback,
): HTMLElement {
    const card = document.createElement("article");

    card.className = "meal-card-large";

    const header = document.createElement("div");

    header.className = "meal-header-large";

    const content = document.createElement("div");

    content.className = "meal-content-large";

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
    const wrapper = document.createElement("button");

    wrapper.type = "button";

    wrapper.className = "meal-title-block";

    const titleRow = document.createElement("div");

    titleRow.className = "meal-title-row";

    const title = document.createElement("span");

    title.className = "meal-title";

    title.textContent = meal.name;

    const icon = document.createElement("span");

    icon.className = "meal-expand-icon";

    icon.innerHTML = ICONS.chevron;

    titleRow.append(
        title,
        icon,
    );

    const meta = document.createElement("div");

    meta.className = "meal-meta-large";

    meta.textContent = [
        `${meal.total_calories ?? 0} ккал`,
        `Б ${meal.total_protein ?? 0}`,
        `Ж ${meal.total_fat ?? 0}`,
        `В ${meal.total_carbs ?? 0}`,
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
    const actions = document.createElement("div");

    actions.className =
        "meal-actions-large";

    const addItem = document.createElement(
        "button",
    );

    addItem.type = "button";

    addItem.className =
        "meal-action-add";

    addItem.textContent =
        "+ Продукт";

    addItem.addEventListener(
        "click",
        () => {
            const mealId =
                document.getElementById(
                    "add-item-meal-id",
                ) as HTMLInputElement | null;

            const name =
                document.getElementById(
                    "add-item-name",
                ) as HTMLInputElement | null;

            const kcal =
                document.getElementById(
                    "add-item-kcal",
                ) as HTMLInputElement | null;

            const protein =
                document.getElementById(
                    "add-item-protein",
                ) as HTMLInputElement | null;

            const fat =
                document.getElementById(
                    "add-item-fat",
                ) as HTMLInputElement | null;

            const carb =
                document.getElementById(
                    "add-item-carb",
                ) as HTMLInputElement | null;

            if (
                !mealId
                || !name
                || !kcal
                || !protein
                || !fat
                || !carb
            ) {
                return;
            }

            mealId.value = String(meal.id);
            name.value = "";
            kcal.value = "0";
            protein.value = "0";
            fat.value = "0";
            carb.value = "0";

            openModal(
                "modal-add-item",
            );
        },
    );

    const edit = createIconButton(
        "meal-action-icon",
        ICONS.pencil,
        "Редагувати прийом",
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

            id.value = String(meal.id);
            name.value = meal.name || "";
            category.value =
                meal.category
                || "Сніданок";
            time.value =
                meal.time || "";

            openModal(
                "modal-edit-meal",
            );
        },
    );

    const remove = createIconButton(
        "meal-action-icon meal-action-delete",
        ICONS.delete,
        "Подвійний клік для видалення",
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
        document.createElement("div");

    container.className =
        "meal-items-large";

    if (!meal.items?.length) {
        const empty =
            document.createElement("div");

        empty.className =
            "meal-items-empty";

        empty.textContent =
            "Продукти ще не додані.";

        container.appendChild(empty);

        return container;
    }

    meal.items.forEach((item) => {
        container.appendChild(
            createItemRow(
                item,
                onRefresh,
            ),
        );
    });

    return container;
}

function createItemRow(
    item: MealItem,
    onRefresh: RefreshCallback,
): HTMLElement {
    const row =
        document.createElement("div");

    row.className =
        "meal-item-row-large";

    const info =
        document.createElement("div");

    info.className =
        "meal-item-info-large";

    const name =
        document.createElement("div");

    name.className =
        "meal-item-name-large";

    name.textContent =
        item.name;

    const macros =
        document.createElement("div");

    macros.className =
        "meal-item-macros-large";

    macros.textContent = [
        `${item.calories ?? 0} ккал`,
        `Б ${item.protein ?? 0}`,
        `Ж ${item.fat ?? 0}`,
        `В ${item.carbs ?? 0}`,
    ].join(" · ");

    info.append(
        name,
        macros,
    );

    const actions =
        document.createElement("div");

    actions.className =
        "meal-item-actions-large";

    const edit = createIconButton(
        "meal-item-action",
        ICONS.pencil,
        "Редагувати продукт",
    );

    edit.addEventListener(
        "click",
        () => {
            const id =
                document.getElementById(
                    "edit-item-id",
                ) as HTMLInputElement | null;

            const name =
                document.getElementById(
                    "edit-item-name",
                ) as HTMLInputElement | null;

            const kcal =
                document.getElementById(
                    "edit-item-kcal",
                ) as HTMLInputElement | null;

            const protein =
                document.getElementById(
                    "edit-item-protein",
                ) as HTMLInputElement | null;

            const fat =
                document.getElementById(
                    "edit-item-fat",
                ) as HTMLInputElement | null;

            const carb =
                document.getElementById(
                    "edit-item-carb",
                ) as HTMLInputElement | null;

            if (
                !id
                || !name
                || !kcal
                || !protein
                || !fat
                || !carb
            ) {
                return;
            }

            id.value =
                String(item.id);

            name.value =
                item.name || "";

            kcal.value =
                String(item.calories ?? 0);

            protein.value =
                String(item.protein ?? 0);

            fat.value =
                String(item.fat ?? 0);

            carb.value =
                String(item.carbs ?? 0);

            openModal(
                "modal-edit-item",
            );
        },
    );

    const remove = createIconButton(
        "meal-item-action meal-item-delete",
        ICONS.delete,
        "Подвійний клік для видалення",
    );

    remove.addEventListener(
        "dblclick",
        async () => {
            await NutritionAPI.deleteItem(
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
        document.createElement("button");

    button.type = "button";

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