import {
    openModal,
} from "../modals/modal.js";

import {
    NutritionAPI,
} from "../api.js";


export function renderMeals(
    meals,
    onRefresh,
) {
    const list = document.getElementById(
        "meals-list"
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
        const card = createMealCard(
            meal,
            onRefresh,
        );

        list.appendChild(card);
    });
}


function createMealCard(
    meal,
    onRefresh,
) {
    const card = document.createElement("div");

    card.className =
        "meal-card-large";

    const header = document.createElement("div");

    header.className =
        "meal-header-large";

    header.append(
        createMealInfo(meal),
        createMealActions(
            meal,
            onRefresh,
        ),
    );

    const items = createMealItems(
        meal,
        onRefresh,
    );

    card.append(
        header,
        items,
    );

    return card;
}


function createMealInfo(meal) {
    const wrapper = document.createElement("div");

    wrapper.className =
        "meal-title-block";

    const title = document.createElement("div");

    title.className =
        "meal-title";

    title.textContent = meal.name;

    const meta = document.createElement("div");

    meta.className =
        "meal-meta-large";

    meta.textContent = [
        meal.category || "—",
        meal.time || "—",
        `${meal.total_calories || 0} ккал`,
    ].join(" · ");

    wrapper.append(
        title,
        meta,
    );

    return wrapper;
}


function createMealActions(
    meal,
    onRefresh,
) {
    const actions = document.createElement("div");

    actions.className =
        "meal-actions-large";

    const addItem = document.createElement(
        "button"
    );

    addItem.className =
        "btn small";

    addItem.textContent =
        "Додати продукт";

    addItem.addEventListener(
        "click",
        () => {
            document.getElementById(
                "add-item-meal-id"
            ).value = meal.id;

            document.getElementById(
                "add-item-name"
            ).value = "";

            document.getElementById(
                "add-item-kcal"
            ).value = 0;

            document.getElementById(
                "add-item-protein"
            ).value = 0;

            document.getElementById(
                "add-item-fat"
            ).value = 0;

            document.getElementById(
                "add-item-carb"
            ).value = 0;

            openModal(
                "modal-add-item"
            );
        }
    );

    const edit = document.createElement(
        "button"
    );

    edit.className =
        "btn small";

    edit.textContent =
        "Редагувати";

    edit.addEventListener(
        "click",
        () => {
            document.getElementById(
                "edit-meal-id"
            ).value = meal.id;

            document.getElementById(
                "edit-meal-name"
            ).value = meal.name || "";

            document.getElementById(
                "edit-meal-category"
            ).value =
                meal.category
                || "Сніданок";

            document.getElementById(
                "edit-meal-time"
            ).value =
                meal.time || "";

            openModal(
                "modal-edit-meal"
            );
        }
    );

    const remove = document.createElement(
        "button"
    );

    remove.className =
        "btn small danger";

    remove.textContent =
        "Видалити";

    remove.addEventListener(
        "click",
        async () => {
            const confirmed = confirm(
                "Видалити цей прийом?"
            );

            if (!confirmed) {
                return;
            }

            await NutritionAPI.deleteMeal(
                meal.id
            );

            onRefresh();
        }
    );

    actions.append(
        addItem,
        edit,
        remove,
    );

    return actions;
}


function createMealItems(
    meal,
    onRefresh,
) {
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
            )
        );
    });

    return container;
}


function createItemRow(
    item,
    onRefresh,
) {
    const row =
        document.createElement("div");

    row.className =
        "meal-item-row-large";

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
        `${item.calories || 0} ккал`,
        `${item.protein || 0} Б`,
        `${item.fat || 0} Ж`,
        `${item.carbs || 0} В`,
    ].join(" · ");

    const actions =
        document.createElement("div");

    actions.className =
        "meal-item-actions-large";

    const edit =
        document.createElement("button");

    edit.className =
        "btn tiny";

    edit.textContent =
        "Ред.";

    edit.addEventListener(
        "click",
        () => {
            document.getElementById(
                "edit-item-id"
            ).value = item.id;

            document.getElementById(
                "edit-item-name"
            ).value = item.name || "";

            document.getElementById(
                "edit-item-kcal"
            ).value =
                item.calories || 0;

            document.getElementById(
                "edit-item-protein"
            ).value =
                item.protein || 0;

            document.getElementById(
                "edit-item-fat"
            ).value =
                item.fat || 0;

            document.getElementById(
                "edit-item-carb"
            ).value =
                item.carbs || 0;

            openModal(
                "modal-edit-item"
            );
        }
    );

    const remove =
        document.createElement("button");

    remove.className =
        "btn tiny danger";

    remove.textContent =
        "×";

    remove.addEventListener(
        "click",
        async () => {
            await NutritionAPI.deleteItem(
                item.id
            );

            onRefresh();
        }
    );

    actions.append(
        edit,
        remove,
    );

    row.append(
        name,
        macros,
        actions,
    );

    return row;
}