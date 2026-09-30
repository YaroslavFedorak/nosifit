import { NutritionAPI, } from "../api.js";
import { closeModal, openModal, } from "./modal.js";
import { getLocale, nutrition_t, } from "../../i18n/index.js";
let selectedProductId = null;
let catalogMode = "favorites";
let catalogProducts = { favorites: [], recent: [], mine: [] };
function formatMacro(value) {
    return Number(value ?? 0).toFixed(1);
}
function formatCalories(value) {
    return String(Math.round(Number(value ?? 0)));
}
function getInputValue(id) {
    const element = document.getElementById(id);
    return element?.value ?? "";
}
function setInputValue(id, value) {
    const element = document.getElementById(id);
    if (element)
        element.value = value;
}
function setSelectValue(id, value) {
    const element = document.getElementById(id);
    if (element)
        element.value = value;
}
function createProductButton(product) {
    const wrapper = document.createElement("div");
    wrapper.className = "nutrition-product-option";
    const select = document.createElement("button");
    select.type = "button";
    select.className = "nutrition-product-select";
    const text = document.createElement("span");
    text.className = "nutrition-product-option-text";
    text.textContent = product.brand ? product.name + " · " + product.brand : product.name;
    const meta = document.createElement("span");
    meta.className = "nutrition-product-option-meta";
    meta.textContent = formatCalories(product.kcal_per_100g) + " " + nutrition_t("units.kcal") + " / 100 g";
    select.append(text, meta);
    select.addEventListener("click", () => selectProduct(product));
    const favorite = document.createElement("button");
    favorite.type = "button";
    favorite.className = "nutrition-product-favorite";
    favorite.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.8l2.55 5.16 5.7.83-4.13 4.03.98 5.69L12 16.82 6.9 19.51l.98-5.69L3.75 9.79l5.7-.83L12 3.8z"></path></svg>';
    favorite.setAttribute("aria-pressed", String(product.is_favorite));
    favorite.setAttribute("aria-label", product.is_favorite ? "Remove from favorites" : "Add to favorites");
    favorite.addEventListener("click", async (event) => {
        event.stopPropagation();
        try {
            await NutritionAPI.setProductFavorite(product.id, !product.is_favorite, getLocale());
            await loadCatalog();
        }
        catch (error) {
            console.error("Failed to update product favorite:", error);
        }
    });
    wrapper.append(select, favorite);
    return wrapper;
}
function getProductSearchText(product) {
    return `${product.name} ${product.brand ?? ""}`.toLocaleLowerCase();
}
function setCatalogSortMode(mode) {
    catalogMode = mode;
    const searching = getInputValue("add-item-search").trim().length > 0;
    document.querySelectorAll("[data-catalog-section]").forEach((section) => {
        const sectionMode = section.dataset.catalogSection;
        section.hidden = searching ? sectionMode !== "search" : sectionMode !== catalogMode;
    });
    document.querySelectorAll("[data-catalog-sort]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.catalogSort === catalogMode));
    });
}
function setCatalogSearchState(query) {
    const searching = query.trim().length > 0;
    document.querySelector(".nutrition-product-sort")?.toggleAttribute("hidden", searching);
    if (searching) {
        document.querySelectorAll("[data-catalog-section]").forEach((section) => {
            section.hidden = section.dataset.catalogSection !== "search";
        });
    }
    else {
        setCatalogSortMode(catalogMode);
    }
    document.querySelector(".nutrition-product-sections")?.classList.toggle("is-searching", searching);
}
function renderProductList(elementId, products) {
    const element = document.getElementById(elementId);
    if (!element)
        return;
    element.innerHTML = "";
    if (!products.length) {
        const empty = document.createElement("div");
        empty.className = "nutrition-product-empty";
        empty.textContent = nutrition_t("catalog.noResults");
        element.appendChild(empty);
        return;
    }
    products.forEach((product) => element.appendChild(createProductButton(product)));
}
function renderSelectedProduct(product) {
    const element = document.getElementById("selected-product");
    if (!element)
        return;
    element.innerHTML = "";
    if (!product)
        return;
    const title = document.createElement("strong");
    title.textContent = product.name;
    const meta = document.createElement("span");
    meta.textContent = product.kcal_per_100g + " " + nutrition_t("units.kcal") + " · "
        + nutrition_t("units.proteinShort") + " " + product.protein_per_100g + " · "
        + nutrition_t("units.fatShort") + " " + product.fat_per_100g + " · "
        + nutrition_t("units.carbsShort") + " " + product.carbs_per_100g;
    element.append(title, meta);
}
function selectProduct(product) {
    selectedProductId = product.id;
    setSelectValue("add-item-unit", product.default_unit);
    setInputValue("add-item-amount", product.default_unit === "pcs" ? "1" : "100");
    renderSelectedProduct(product);
}
async function loadCatalog() {
    const locale = getLocale();
    try {
        const [favorites, recent, mine] = await Promise.all([
            NutritionAPI.getFavoriteProducts(locale),
            NutritionAPI.getRecentProducts(locale),
            NutritionAPI.getMyProducts(locale),
        ]);
        catalogProducts = {
            favorites: favorites.products,
            recent: recent.products,
            mine: mine.products,
        };
        renderProductList("product-favorites", catalogProducts.favorites);
        renderProductList("product-recent", catalogProducts.recent);
        renderProductList("product-mine", catalogProducts.mine);
    }
    catch (error) {
        console.error("Failed to load nutrition catalog:", error);
    }
}
async function searchCatalog(query) {
    setCatalogSearchState(query);
    if (!query.trim()) {
        renderProductList("product-search-results", []);
        return;
    }
    const normalizedQuery = query.trim().toLocaleLowerCase();
    const products = catalogProducts[catalogMode].filter((product) => getProductSearchText(product).includes(normalizedQuery));
    renderProductList("product-search-results", products);
}
export function openAddItemModal(mealId) {
    selectedProductId = null;
    setInputValue("add-item-meal-id", String(mealId));
    setInputValue("add-item-search", "");
    setInputValue("add-item-amount", "100");
    catalogMode = "favorites";
    setSelectValue("add-item-unit", "g");
    renderSelectedProduct(null);
    openModal("modal-add-item");
    setCatalogSearchState("");
    void loadCatalog();
}
export async function openEditItemModal(item) {
    const id = document.getElementById("edit-item-id");
    const product = document.getElementById("edit-item-product");
    const meal = document.getElementById("edit-item-meal-id");
    const amount = document.getElementById("edit-item-amount");
    const unit = document.getElementById("edit-item-unit");
    if (!id || !product || !meal || !amount || !unit)
        return;
    id.value = String(item.id);
    product.value = item.name;
    amount.value = String(item.amount ?? item.weight ?? 100);
    unit.value = item.unit ?? "g";
    try {
        const day = await NutritionAPI.getDay(getLocale());
        meal.innerHTML = "";
        day.meals.forEach((entry) => {
            const option = document.createElement("option");
            option.value = String(entry.id);
            option.textContent = entry.name;
            meal.appendChild(option);
        });
        const currentMeal = day.meals.find((entry) => entry.items?.some((entryItem) => entryItem.id === item.id));
        if (currentMeal)
            meal.value = String(currentMeal.id);
    }
    catch (error) {
        console.error("Failed to load meals:", error);
    }
    openModal("modal-edit-item");
}
export function setupItemModals(onRefresh) {
    document.getElementById("close-add-item")?.addEventListener("click", () => closeModal("modal-add-item"));
    document.getElementById("save-add-item")?.addEventListener("click", async () => {
        if (selectedProductId === null)
            return;
        const mealId = Number(getInputValue("add-item-meal-id"));
        const amount = Number(getInputValue("add-item-amount"));
        const unit = getInputValue("add-item-unit");
        if (!mealId || !Number.isFinite(amount) || amount <= 0)
            return;
        try {
            await NutritionAPI.createEntry({ meal_id: mealId, product_id: selectedProductId, amount, unit, locale: getLocale() });
            closeModal("modal-add-item");
            await onRefresh();
        }
        catch (error) {
            console.error("Failed to add food entry:", error);
        }
    });
    document.querySelectorAll("[data-catalog-sort]").forEach((button) => {
        button.addEventListener("click", () => {
            const mode = button.dataset.catalogSort;
            if (mode) setCatalogSortMode(mode);
        });
    });
    document.querySelectorAll("[data-catalog-sort]").forEach((button) => {
        button.addEventListener("click", () => {
            const mode = button.dataset.catalogSort;
            if (mode)
                setCatalogSortMode(mode);
        });
    });
    document.getElementById("add-item-unit")?.addEventListener("change", (event) => {
        const target = event.target;
        setInputValue("add-item-amount", target.value === "pcs" ? "1" : "100");
    });
    document.getElementById("add-item-search")?.addEventListener("input", (event) => {
        const target = event.target;
        void searchCatalog(target.value);
    });
    document.getElementById("close-edit-item")?.addEventListener("click", () => closeModal("modal-edit-item"));
    document.getElementById("save-edit-item")?.addEventListener("click", async () => {
        const id = Number(getInputValue("edit-item-id"));
        const mealId = Number(getInputValue("edit-item-meal-id"));
        const amount = Number(getInputValue("edit-item-amount"));
        const unit = getInputValue("edit-item-unit");
        if (!id || !mealId || !Number.isFinite(amount) || amount <= 0)
            return;
        try {
            await NutritionAPI.updateEntry(id, { meal_id: mealId, amount, unit, locale: getLocale() });
            closeModal("modal-edit-item");
            await onRefresh();
        }
        catch (error) {
            console.error("Failed to update food entry:", error);
        }
    });
    document.getElementById("open-add-my-product")?.addEventListener("click", () => {
        ["product-name", "product-brand", "product-kcal", "product-protein", "product-fat", "product-carbs"].forEach((id) => setInputValue(id, ""));
        setInputValue("product-fiber", "0");
        setInputValue("product-grams-per-unit", "1");
        setSelectValue("product-unit", "g");
        openModal("modal-add-product");
    });
    document.getElementById("close-add-product")?.addEventListener("click", () => closeModal("modal-add-product"));
    document.getElementById("save-add-product")?.addEventListener("click", async () => {
        const name = getInputValue("product-name").trim();
        if (!name)
            return;
        try {
            const product = await NutritionAPI.createProduct({
                name,
                brand: getInputValue("product-brand"),
                locale: getLocale(),
                kcal_per_100g: Number(getInputValue("product-kcal") || 0),
                protein_per_100g: Number(getInputValue("product-protein") || 0),
                fat_per_100g: Number(getInputValue("product-fat") || 0),
                carbs_per_100g: Number(getInputValue("product-carbs") || 0),
                fiber_per_100g: Number(getInputValue("product-fiber") || 0),
                default_unit: getInputValue("product-unit"),
                grams_per_unit: Number(getInputValue("product-grams-per-unit") || 1),
            });
            selectedProductId = product.id;
            setSelectValue("add-item-unit", product.default_unit);
            renderSelectedProduct(product);
            closeModal("modal-add-product");
            await loadCatalog();
        }
        catch (error) {
            console.error("Failed to create user product:", error);
        }
    });
}
