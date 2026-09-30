import { NutritionAPI } from "../api.js";
import { closeModal, openModal } from "./modal.js";
import { getLocale, nutrition_t } from "../../i18n/index.js";
import type { Meal, MealItem, Product, NutritionUnit } from "../types.js";

type RefreshCallback = () => void | Promise<void>;

let selectedProductId: number | null = null;
let selectedProduct: Product | null = null;

interface PendingMealItem {
    productId: number;
    product: Product;
    amount: number;
    unit: NutritionUnit;
}

let pendingMealItems: PendingMealItem[] = [];
type CatalogMode = "favorites" | "recent" | "mine" | "all";
let catalogMode: CatalogMode = "all";
let catalogProducts: Record<CatalogMode, Product[]> = {
    favorites: [],
    recent: [],
    mine: [],
    all: [],
};

function formatMacro(value: number | null | undefined): string {
    return Number(value ?? 0).toFixed(1);
}

function formatCalories(value: number | null | undefined): string {
    return String(Math.round(Number(value ?? 0)));
}

function getInputValue(id: string): string {
    const element = document.getElementById(id) as HTMLInputElement | null;
    return element?.value ?? "";
}

function setInputValue(id: string, value: string): void {
    const element = document.getElementById(id) as HTMLInputElement | null;
    if (element) element.value = value;
}

function setSelectValue(id: string, value: string): void {
    const element = document.getElementById(id) as HTMLSelectElement | null;
    if (element) element.value = value;
}

function createProductButton(product: Product): HTMLElement {
    const wrapper = document.createElement("div");
    wrapper.className = "nutrition-product-option";

    const select = document.createElement("button");
    select.type = "button";
    select.className = "nutrition-product-select";

    const text = document.createElement("span");
    text.className = "nutrition-product-option-text";
    text.textContent = product.brand ? `${product.name} · ${product.brand}` : product.name;

    const meta = document.createElement("span");
    meta.className = "nutrition-product-option-meta";
    meta.textContent = `${formatCalories(product.kcal_per_100g)} ${nutrition_t("units.kcal")} / 100 g`;

    select.append(text, meta);
    select.addEventListener("click", () => selectProduct(product));

    const favorite = document.createElement("button");
    favorite.type = "button";
    favorite.className = "nutrition-product-favorite";
    favorite.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.8l2.55 5.16 5.7.83-4.13 4.03.98 5.69L12 16.82 6.9 19.51l.98-5.69L3.75 9.79l5.7-.83L12 3.8z"></path></svg>';
    favorite.setAttribute("aria-label", product.name);

    favorite.setAttribute("aria-pressed", String(product.is_favorite));
    favorite.setAttribute("aria-label", product.is_favorite ? "Remove from favorites" : "Add to favorites");
    favorite.addEventListener("click", async (event) => {
        event.stopPropagation();
        try {
            await NutritionAPI.setProductFavorite(product.id, !product.is_favorite, getLocale());
            await loadCatalog();
        } catch (error) {
            console.error("Failed to update product favorite:", error);
        }
    });

    wrapper.append(select, favorite);
    return wrapper;
}

function getProductSearchText(product: Product): string {
    return `${product.name} ${product.brand ?? ""}`.toLocaleLowerCase();
}

function setCatalogSortMode(mode: CatalogMode): void {
    catalogMode = mode;
    const searching = getInputValue("add-item-search").trim().length > 0;

    document.querySelectorAll<HTMLElement>("[data-catalog-section]").forEach((section) => {
        const sectionMode = section.dataset.catalogSection;
        section.hidden = searching
            ? sectionMode !== "search"
            : sectionMode !== catalogMode;
    });

    document.querySelectorAll<HTMLButtonElement>("[data-catalog-sort]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.catalogSort === catalogMode));
    });
}

function setCatalogSearchState(query: string): void {
    const searching = query.trim().length > 0;
    if (searching) {
        document.querySelectorAll<HTMLElement>("[data-catalog-section]").forEach((section) => {
            section.hidden = section.dataset.catalogSection !== "search";
        });
    } else {
        setCatalogSortMode(catalogMode);
    }

    document.querySelector(".nutrition-product-sections")?.classList.toggle("is-searching", searching);
}

function renderProductList(elementId: string, products: Product[]): void {
    const element = document.getElementById(elementId);
    if (!element) return;

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

function renderSelectedProduct(product: Product | null): void {
    const element = document.getElementById("selected-product");
    if (!element) return;

    element.innerHTML = "";

    if (!product) {
        const empty = document.createElement("span");
        empty.textContent = nutrition_t("catalog.selectedProduct");
        element.appendChild(empty);
        return;
    }

    const title = document.createElement("strong");
    title.textContent = product.name;

    const meta = document.createElement("span");
    meta.textContent =
        `${product.kcal_per_100g} ${nutrition_t("units.kcal")} · ${nutrition_t("units.proteinShort")} ${product.protein_per_100g} · ${nutrition_t("units.fatShort")} ${product.fat_per_100g} · ${nutrition_t("units.carbsShort")} ${product.carbs_per_100g}`;

    element.append(title, meta);
}

function selectProduct(product: Product): void {
    selectedProductId = product.id;
    selectedProduct = product;
    setSelectValue("add-item-unit", product.default_unit);
    setInputValue("add-item-amount", product.default_unit === "pcs" ? "1" : "100");
    renderSelectedProduct(product);
}

function renderPendingMealItems(): void {
    const container = document.getElementById("pending-meal-items");
    if (!container) return;

    container.innerHTML = "";

    if (!pendingMealItems.length) {
        container.hidden = true;
        return;
    }

    container.hidden = false;

    pendingMealItems.forEach((entry, index) => {
        const row = document.createElement("div");
        row.className = "nutrition-pending-item";

        const info = document.createElement("div");
        info.className = "nutrition-pending-item-info";

        const name = document.createElement("strong");
        name.textContent = entry.product.brand
            ? `${entry.product.name} · ${entry.product.brand}`
            : entry.product.name;

        const amount = document.createElement("span");
        amount.textContent = `${entry.amount} ${entry.unit}`;

        info.append(name, amount);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "nutrition-pending-item-remove";
        remove.textContent = "×";
        remove.setAttribute("aria-label", entry.product.name);
        remove.addEventListener("click", () => {
            pendingMealItems.splice(index, 1);
            renderPendingMealItems();
        });

        row.append(info, remove);
        container.appendChild(row);
    });
}

function queueSelectedProduct(): void {
    if (selectedProductId === null) return;

    const amount = Number(getInputValue("add-item-amount"));
    const unit = getInputValue("add-item-unit") as NutritionUnit;

    if (!Number.isFinite(amount) || amount <= 0) return;

    const product = selectedProduct;
    if (!product) return;

    pendingMealItems.push({
        productId: product.id,
        product,
        amount,
        unit,
    });

    selectedProductId = null;
    selectedProduct = null;
    setInputValue("add-item-amount", "100");
    setSelectValue("add-item-unit", "g");
    renderSelectedProduct(null);
    renderPendingMealItems();
}

async function loadCatalog(): Promise<void> {
    const locale = getLocale();
    try {
        const [all, favorites, recent, mine] = await Promise.all([
            NutritionAPI.getProducts("", locale),
            NutritionAPI.getFavoriteProducts(locale),
            NutritionAPI.getRecentProducts(locale),
            NutritionAPI.getMyProducts(locale),
        ]);

        catalogProducts = {
            all: all.products,
            favorites: favorites.products,
            recent: recent.products,
            mine: mine.products,
        };

        renderProductList("product-all", catalogProducts.all);

        renderProductList("product-favorites", catalogProducts.favorites);
        renderProductList("product-recent", catalogProducts.recent);
        renderProductList("product-mine", catalogProducts.mine);
    } catch (error) {
        console.error("Failed to load nutrition catalog:", error);
    }
}

let catalogSearchRequest = 0;

async function searchCatalog(query: string): Promise<void> {
    setCatalogSearchState(query);

    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
        renderProductList("product-search-results", []);
        return;
    }

    const requestId = ++catalogSearchRequest;

    if (catalogMode === "all") {
        try {
            const response = await NutritionAPI.getProducts(normalizedQuery, getLocale());
            if (requestId !== catalogSearchRequest || catalogMode !== "all") return;
            renderProductList("product-search-results", response.products);
        } catch (error) {
            if (requestId === catalogSearchRequest) {
                console.error("Failed to search nutrition catalog:", error);
                renderProductList("product-search-results", []);
            }
        }
        return;
    }

    const products = catalogProducts[catalogMode].filter((product) =>
        getProductSearchText(product).includes(normalizedQuery.toLocaleLowerCase()),
    );

    if (requestId === catalogSearchRequest) {
        renderProductList("product-search-results", products);
    }
}

export function openAddItemModal(mealId: number, meal?: Meal): void {
    selectedProductId = null;
    selectedProduct = null;
    setInputValue("add-item-meal-id", String(mealId));
    setInputValue("add-meal-name", meal?.name ?? "");
    setInputValue("add-meal-category", meal?.category ?? "Сніданок");
    setInputValue("add-meal-time", meal?.time ?? "");
    setInputValue("add-item-search", "");
    setInputValue("add-item-amount", "100");
    catalogMode = "all";
    setSelectValue("add-item-unit", "g");
    renderSelectedProduct(null);
    openModal("modal-add-item");
    setCatalogSearchState("");
    setCatalogSortMode(catalogMode);
    void loadCatalog();
}

export async function openEditItemModal(item: MealItem): Promise<void> {
    const id = document.getElementById("edit-item-id") as HTMLInputElement | null;
    const product = document.getElementById("edit-item-product") as HTMLInputElement | null;
    const meal = document.getElementById("edit-item-meal-id") as HTMLSelectElement | null;
    const amount = document.getElementById("edit-item-amount") as HTMLInputElement | null;
    const unit = document.getElementById("edit-item-unit") as HTMLSelectElement | null;

    if (!id || !product || !meal || !amount || !unit) return;

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

        const currentMeal = day.meals.find(
            (entry) => entry.items?.some((entryItem) => entryItem.id === item.id),
        );

        if (currentMeal) meal.value = String(currentMeal.id);
    } catch (error) {
        console.error("Failed to load meals:", error);
    }

    openModal("modal-edit-item");
}

export function setupItemModals(onRefresh: RefreshCallback): void {
    document.getElementById("close-add-item")?.addEventListener(
        "click",
        () => {
            pendingMealItems = [];
            renderPendingMealItems();
            closeModal("modal-add-item");
        },
    );

    document.getElementById("add-item-to-meal")?.addEventListener(
        "click",
        () => queueSelectedProduct(),
    );

    document.getElementById("open-add-meal")?.addEventListener(
        "click",
        () => openAddItemModal(0),
    );

    document.getElementById("save-add-item")?.addEventListener(
        "click",
        async () => {
            let mealId = Number(getInputValue("add-item-meal-id"));
            const mealName = getInputValue("add-meal-name").trim();

            if (!mealName || !pendingMealItems.length) return;

            try {
                const mealPayload = {
                    name: mealName,
                    category: getInputValue("add-meal-category"),
                    time: getInputValue("add-meal-time") || null,
                };

                if (mealId) {
                    await NutritionAPI.updateMeal(mealId, mealPayload);
                } else {
                    const meal = await NutritionAPI.createMeal(mealPayload);
                    mealId = meal.id;
                }

                await Promise.all(
                    pendingMealItems.map((entry) =>
                        NutritionAPI.createEntry({
                            meal_id: mealId,
                            product_id: entry.productId,
                            amount: entry.amount,
                            unit: entry.unit,
                            locale: getLocale(),
                        }),
                    ),
                );

                pendingMealItems = [];
                renderPendingMealItems();
                closeModal("modal-add-item");
                await onRefresh();
            } catch (error) {
                console.error("Failed to save meal and food items:", error);
            }
        },
    );

    document.querySelectorAll<HTMLButtonElement>("[data-catalog-sort]").forEach((button) => {
        button.addEventListener("click", () => {
            const mode = button.dataset.catalogSort as CatalogMode | undefined;
            if (mode) {
                setCatalogSortMode(mode);
                void searchCatalog(getInputValue("add-item-search"));
            }
        });
    });

    document.getElementById("add-item-unit")?.addEventListener("change", (event) => {
        const target = event.target as HTMLSelectElement;
        setInputValue("add-item-amount", target.value === "pcs" ? "1" : "100");
    });

    document.getElementById("add-item-search")?.addEventListener(
        "input",
        (event) => {
            const target = event.target as HTMLInputElement;
            void searchCatalog(target.value);
        },
    );

    document.getElementById("close-edit-item")?.addEventListener(
        "click",
        () => closeModal("modal-edit-item"),
    );

    document.getElementById("save-edit-item")?.addEventListener(
        "click",
        async () => {
            const id = Number(getInputValue("edit-item-id"));
            const mealId = Number(getInputValue("edit-item-meal-id"));
            const amount = Number(getInputValue("edit-item-amount"));
            const unit = getInputValue("edit-item-unit") as NutritionUnit;

            if (!id || !mealId || !Number.isFinite(amount) || amount <= 0) return;

            try {
                await NutritionAPI.updateEntry(id, {
                    meal_id: mealId,
                    amount,
                    unit,
                    locale: getLocale(),
                });

                closeModal("modal-edit-item");
                await onRefresh();
            } catch (error) {
                console.error("Failed to update food entry:", error);
            }
        },
    );

    document.getElementById("open-add-my-product")?.addEventListener(
        "click",
        () => {
            [
                "product-name",
                "product-brand",
                "product-kcal",
                "product-protein",
                "product-fat",
                "product-carbs",
            ].forEach((id) => setInputValue(id, ""));

            setInputValue("product-fiber", "0");
            setInputValue("product-grams-per-unit", "1");
            setSelectValue("product-unit", "g");
            openModal("modal-add-product");
        },
    );

    document.getElementById("close-add-product")?.addEventListener(
        "click",
        () => closeModal("modal-add-product"),
    );

    document.getElementById("save-add-product")?.addEventListener(
        "click",
        async () => {
            const name = getInputValue("product-name").trim();
            if (!name) return;

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
                    default_unit: getInputValue("product-unit") as NutritionUnit,
                    grams_per_unit: Number(getInputValue("product-grams-per-unit") || 1),
                });

                selectedProductId = product.id;
                setSelectValue("add-item-unit", product.default_unit);
                setInputValue("add-item-amount", product.default_unit === "pcs" ? "1" : "100");
                renderSelectedProduct(product);
                closeModal("modal-add-product");
                await loadCatalog();
            } catch (error) {
                console.error("Failed to create user product:", error);
            }
        },
    );
}
