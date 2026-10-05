/**
 * Food picker + "my product" + edit-entry modals.
 * Shared by the Nutrition page and the Dashboard.
 */
import { NutritionAPI } from "../api.js";
import {
    formatAmount,
    mealCategoryLabel,
    normalizeMealCategory,
    suggestMealCategory,
    unitLabel,
} from "../categories.js";
import { describeError } from "../errors.js";
import { getLocale, nutrition_t } from "../../i18n/index.js";
import type { Meal, MealItem, NutritionUnit, Product } from "../types.js";
import {
    closeModal,
    emitNutritionChange,
    getValue,
    markInvalid,
    onClick,
    openModal,
    parseNumber,
    setBusy,
    setModalError,
    setValue,
} from "./modal.js";

type RefreshCallback = () => void | Promise<void>;
type CatalogMode = "favorites" | "recent" | "mine" | "all";

interface PendingMealItem {
    product: Product;
    amount: number;
    unit: NutritionUnit;
}

const PICKER_ID = "modal-add-item";
const PRODUCT_ID = "modal-add-product";
const EDIT_ID = "modal-edit-item";

const MAX_AMOUNT: Record<NutritionUnit, number> = { g: 5000, ml: 5000, pcs: 100 };

const STAR_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.8l2.55 5.16 5.7.83-4.13 4.03.98 5.69L12 16.82 6.9 19.51l.98-5.69L3.75 9.79l5.7-.83L12 3.8z"></path></svg>';
const REMOVE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>';
const CHECK_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>';

let selectedProduct: Product | null = null;
let pendingMealItems: PendingMealItem[] = [];
let existingMealItems: MealItem[] = [];
let catalogMode: CatalogMode = "all";
let catalogProducts: Record<CatalogMode, Product[]> = { favorites: [], recent: [], mine: [], all: [] };
let catalogSearchRequest = 0;
let searchDebounce: number | undefined;

function formatCalories(value: number | null | undefined): string {
    return String(Math.round(Number(value ?? 0)));
}

function formatMacro(value: number | null | undefined): string {
    const number = Number(value ?? 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function defaultAmount(unit: NutritionUnit): string {
    return unit === "pcs" ? "1" : "100";
}

/* ---------- Rendering ---------- */

function createProductRow(product: Product): HTMLElement {
    const wrapper = document.createElement("div");
    wrapper.className = "nf-product";

    const select = document.createElement("button");
    select.type = "button";
    select.className = "nf-product-select";
    select.setAttribute("aria-pressed", String(selectedProduct?.id === product.id));
    select.dataset.productId = String(product.id);

    const name = document.createElement("span");
    name.className = "nf-product-name";
    name.textContent = product.name;

    if (product.brand) {
        const brand = document.createElement("span");
        brand.className = "nf-product-brand";
        brand.textContent = ` · ${product.brand}`;
        name.appendChild(brand);
    }

    const meta = document.createElement("span");
    meta.className = "nf-product-meta";
    meta.textContent = `${formatCalories(product.kcal_per_100g)} ${nutrition_t("units.kcal")} ${nutrition_t("catalog.per100gShort")}`;

    select.append(name, meta);
    select.addEventListener("click", () => selectProduct(product));
    select.addEventListener("dblclick", () => {
        selectProduct(product);
        queueSelectedProduct();
    });

    const favorite = document.createElement("button");
    favorite.type = "button";
    favorite.className = "nf-product-favorite";
    favorite.innerHTML = STAR_ICON;
    favorite.setAttribute("aria-pressed", String(product.is_favorite));
    const favoriteLabel = nutrition_t(product.is_favorite ? "catalog.favoriteRemove" : "catalog.favoriteAdd");
    favorite.setAttribute("aria-label", favoriteLabel);
    favorite.title = favoriteLabel;

    favorite.addEventListener("click", async (event) => {
        event.stopPropagation();
        favorite.disabled = true;
        try {
            await NutritionAPI.setProductFavorite(product.id, !product.is_favorite, getLocale());
            await loadCatalog();
            if (getValue("add-item-search").trim()) {
                await searchCatalog(getValue("add-item-search"));
            }
        } catch (error) {
            setModalError(PICKER_ID, describeError(error));
        } finally {
            favorite.disabled = false;
        }
    });

    wrapper.append(select, favorite);
    return wrapper;
}

function emptyTextFor(elementId: string): string {
    switch (elementId) {
        case "product-favorites":
            return nutrition_t("catalog.emptyFavorites");
        case "product-recent":
            return nutrition_t("catalog.emptyRecent");
        case "product-mine":
            return nutrition_t("catalog.emptyMine");
        default:
            return nutrition_t("catalog.noResults");
    }
}

function renderProductList(elementId: string, products: Product[]): void {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.innerHTML = "";

    if (!products.length) {
        const empty = document.createElement("div");
        empty.className = "nf-product-empty";
        empty.textContent = emptyTextFor(elementId);
        element.appendChild(empty);
        return;
    }

    products.forEach((product) => element.appendChild(createProductRow(product)));
}

function refreshSelectionState(): void {
    document
        .querySelectorAll<HTMLButtonElement>(`#${PICKER_ID} .nf-product-select`)
        .forEach((button) => {
            button.setAttribute("aria-pressed", String(Number(button.dataset.productId) === selectedProduct?.id));
        });

    const add = document.getElementById("add-item-to-meal") as HTMLButtonElement | null;
    if (add) add.disabled = selectedProduct === null;
}

function renderSelectedProduct(): void {
    const element = document.getElementById("selected-product");
    if (!element) return;

    element.innerHTML = "";
    element.classList.toggle("is-empty", selectedProduct === null);

    if (!selectedProduct) {
        const hint = document.createElement("span");
        hint.textContent = nutrition_t("catalog.selectHint");
        element.appendChild(hint);
        refreshSelectionState();
        return;
    }

    const title = document.createElement("strong");
    title.textContent = selectedProduct.name;

    const meta = document.createElement("span");
    meta.textContent = [
        `${formatCalories(selectedProduct.kcal_per_100g)} ${nutrition_t("units.kcal")}`,
        `${nutrition_t("units.proteinShort")} ${formatMacro(selectedProduct.protein_per_100g)}`,
        `${nutrition_t("units.fatShort")} ${formatMacro(selectedProduct.fat_per_100g)}`,
        `${nutrition_t("units.carbsShort")} ${formatMacro(selectedProduct.carbs_per_100g)}`,
    ].join(" · ") + ` ${nutrition_t("catalog.per100gShort")}`;

    element.append(title, meta);
    refreshSelectionState();
}

function createPendingRow(
    name: string,
    amount: string,
    options: { existing: boolean; onRemove?: () => void },
): HTMLElement {
    const row = document.createElement("div");
    row.className = options.existing ? "nf-pending-item is-existing" : "nf-pending-item";

    const title = document.createElement("span");
    title.className = "nf-pending-name";
    title.textContent = name;

    const quantity = document.createElement("span");
    quantity.className = "nf-pending-amount";
    quantity.textContent = amount;

    row.append(title, quantity);

    if (options.onRemove) {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "nf-pending-remove";
        remove.innerHTML = REMOVE_ICON;
        const label = `${nutrition_t("actions.remove")}: ${name}`;
        remove.setAttribute("aria-label", label);
        remove.title = label;
        remove.addEventListener("click", options.onRemove);
        row.appendChild(remove);
    } else {
        const status = document.createElement("span");
        status.className = "nf-pending-status";
        status.innerHTML = CHECK_ICON;
        status.title = nutrition_t("catalog.alreadyAdded");
        status.setAttribute("aria-label", nutrition_t("catalog.alreadyAdded"));
        row.appendChild(status);
    }

    return row;
}

function pendingCalories(): number {
    return pendingMealItems.reduce((sum, entry) => {
        const grams = entry.unit === "pcs"
            ? entry.amount * Number(entry.product.grams_per_unit || 0)
            : entry.unit === "ml"
                ? entry.amount * Number(entry.product.grams_per_unit || 1)
                : entry.amount;
        return sum + (Number(entry.product.kcal_per_100g || 0) * grams) / 100;
    }, 0);
}

function renderPendingMealItems(): void {
    const container = document.getElementById("pending-meal-items");
    const empty = document.getElementById("pending-meal-items-empty");
    const total = document.getElementById("pending-meal-total");
    if (!container || !empty) return;

    container.innerHTML = "";

    const hasItems = existingMealItems.length > 0 || pendingMealItems.length > 0;
    container.hidden = !hasItems;
    empty.hidden = hasItems;

    if (total) {
        total.textContent = pendingMealItems.length
            ? `+${Math.round(pendingCalories())} ${nutrition_t("units.kcal")}`
            : "";
    }

    existingMealItems.forEach((item) => {
        container.appendChild(
            createPendingRow(item.name, formatAmount(item.amount, item.unit), { existing: true }),
        );
    });

    pendingMealItems.forEach((entry, index) => {
        container.appendChild(
            createPendingRow(entry.product.name, formatAmount(entry.amount, entry.unit), {
                existing: false,
                onRemove: () => {
                    pendingMealItems.splice(index, 1);
                    renderPendingMealItems();
                },
            }),
        );
    });

    container.scrollTop = container.scrollHeight;
}

/* ---------- Selection ---------- */

function selectProduct(product: Product): void {
    selectedProduct = product;
    setValue("add-item-unit", product.default_unit);
    setValue("add-item-amount", defaultAmount(product.default_unit));
    markInvalid("add-item-amount", false);
    setModalError(PICKER_ID, null);
    renderSelectedProduct();

    const amount = document.getElementById("add-item-amount") as HTMLInputElement | null;
    if (amount && window.matchMedia("(pointer: fine)").matches) {
        amount.focus();
        amount.select();
    }
}

/** Moves the selected product into the meal. Returns false when the amount is invalid. */
function queueSelectedProduct(): boolean {
    if (!selectedProduct) {
        setModalError(PICKER_ID, nutrition_t("errors.selectProduct"));
        return false;
    }

    const unit = (getValue("add-item-unit") || selectedProduct.default_unit) as NutritionUnit;
    const amount = parseNumber(getValue("add-item-amount"));

    if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_AMOUNT[unit]) {
        markInvalid("add-item-amount", true);
        setModalError(PICKER_ID, nutrition_t("errors.amount", { max: MAX_AMOUNT[unit], unit: unitLabel(unit) }));
        return false;
    }

    markInvalid("add-item-amount", false);
    setModalError(PICKER_ID, null);

    pendingMealItems.push({ product: selectedProduct, amount, unit });
    selectedProduct = null;
    setValue("add-item-amount", "100");
    setValue("add-item-unit", "g");
    renderSelectedProduct();
    renderPendingMealItems();

    const search = document.getElementById("add-item-search") as HTMLInputElement | null;
    if (search && search.value && window.matchMedia("(pointer: fine)").matches) {
        search.select();
        search.focus();
    }

    return true;
}

/* ---------- Catalog ---------- */

function setCatalogMode(mode: CatalogMode): void {
    catalogMode = mode;
    applyCatalogVisibility();
    document.querySelectorAll<HTMLButtonElement>(`#${PICKER_ID} [data-catalog-sort]`).forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.catalogSort === catalogMode));
    });
}

function applyCatalogVisibility(): void {
    const searching = getValue("add-item-search").trim().length > 0;
    document.querySelectorAll<HTMLElement>(`#${PICKER_ID} [data-catalog-section]`).forEach((section) => {
        const sectionMode = section.dataset.catalogSection;
        section.hidden = searching ? sectionMode !== "search" : sectionMode !== catalogMode;
    });
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
        refreshSelectionState();
    } catch (error) {
        setModalError(PICKER_ID, describeError(error));
    }
}

async function searchCatalog(query: string): Promise<void> {
    applyCatalogVisibility();

    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
        renderProductList("product-search-results", []);
        return;
    }

    const requestId = ++catalogSearchRequest;

    if (catalogMode === "all") {
        try {
            const response = await NutritionAPI.getProducts(normalizedQuery, getLocale());
            if (requestId !== catalogSearchRequest) return;
            renderProductList("product-search-results", response.products);
            refreshSelectionState();
        } catch (error) {
            if (requestId === catalogSearchRequest) {
                renderProductList("product-search-results", []);
                setModalError(PICKER_ID, describeError(error));
            }
        }
        return;
    }

    const needle = normalizedQuery.toLocaleLowerCase();
    const products = catalogProducts[catalogMode].filter((product) =>
        `${product.name} ${product.brand ?? ""}`.toLocaleLowerCase().includes(needle),
    );

    if (requestId === catalogSearchRequest) {
        renderProductList("product-search-results", products);
        refreshSelectionState();
    }
}

/* ---------- Public API ---------- */

/** Opens the picker. `mealId = 0` creates a new meal on save. */
export function openAddItemModal(mealId: number, meal?: Meal): void {
    selectedProduct = null;
    existingMealItems = meal?.items ? [...meal.items] : [];
    pendingMealItems = [];
    catalogMode = "all";

    setValue("add-item-meal-id", String(mealId));
    setValue("add-meal-category", normalizeMealCategory(meal?.category ?? meal?.name) ?? suggestMealCategory());
    setValue("add-meal-time", meal?.time ?? "");
    setValue("add-item-search", "");
    setValue("add-item-amount", "100");
    setValue("add-item-unit", "g");
    markInvalid("add-item-amount", false);

    const title = document.getElementById("add-item-title");
    if (title) {
        title.textContent = mealId
            ? (title.dataset.titleExisting ?? nutrition_t("items.addTitle"))
            : (title.dataset.titleNew ?? nutrition_t("meals.addTitle"));
    }

    renderSelectedProduct();
    renderPendingMealItems();
    setCatalogMode(catalogMode);
    openModal(PICKER_ID, "#add-item-search");
    void loadCatalog();
}

export async function openEditItemModal(item: MealItem): Promise<void> {
    const meal = document.getElementById("edit-item-meal-id") as HTMLSelectElement | null;
    if (!meal) return;

    setValue("edit-item-id", String(item.id));
    setValue("edit-item-product", item.name);
    setValue("edit-item-amount", String(item.amount ?? item.weight ?? 100));
    setValue("edit-item-unit", item.unit ?? "g");
    markInvalid("edit-item-amount", false);

    meal.innerHTML = "";
    openModal(EDIT_ID, "#edit-item-amount");

    try {
        const day = await NutritionAPI.getDay(getLocale());

        day.meals.forEach((entry) => {
            const option = document.createElement("option");
            option.value = String(entry.id);
            option.textContent = entry.time
                ? `${mealCategoryLabel(entry.category ?? entry.name)} · ${entry.time}`
                : mealCategoryLabel(entry.category ?? entry.name);
            meal.appendChild(option);
        });

        const currentMeal = day.meals.find(
            (entry) => entry.items?.some((entryItem) => entryItem.id === item.id),
        );
        if (currentMeal) meal.value = String(currentMeal.id);
    } catch (error) {
        setModalError(EDIT_ID, describeError(error));
    }
}

export function setupItemModals(onRefresh: RefreshCallback): void {
    onClick(["open-add-meal", "dashboard-open-add-meal"], () => openAddItemModal(0));

    onClick(["close-add-item"], () => closeModal(PICKER_ID));

    onClick(["add-item-to-meal"], () => {
        queueSelectedProduct();
    });

    document.getElementById("add-item-amount")?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            queueSelectedProduct();
        }
    });

    document.getElementById("add-item-unit")?.addEventListener("change", () => {
        setValue("add-item-amount", defaultAmount(getValue("add-item-unit") as NutritionUnit));
    });

    document.querySelectorAll<HTMLButtonElement>(`#${PICKER_ID} [data-catalog-sort]`).forEach((button) => {
        button.addEventListener("click", () => {
            const mode = button.dataset.catalogSort as CatalogMode | undefined;
            if (!mode) return;
            setCatalogMode(mode);
            void searchCatalog(getValue("add-item-search"));
        });
    });

    document.getElementById("add-item-search")?.addEventListener("input", () => {
        applyCatalogVisibility();
        window.clearTimeout(searchDebounce);
        searchDebounce = window.setTimeout(() => {
            void searchCatalog(getValue("add-item-search"));
        }, 200);
    });

    const saveItems = document.getElementById("save-add-item") as HTMLButtonElement | null;

    saveItems?.addEventListener("click", async () => {
        // A product that is selected but not yet added is clearly meant to be saved too.
        if (selectedProduct && !queueSelectedProduct()) return;

        if (!pendingMealItems.length) {
            setModalError(PICKER_ID, nutrition_t("errors.noItems"));
            return;
        }

        const category = normalizeMealCategory(getValue("add-meal-category")) ?? suggestMealCategory();
        let mealId = Number(getValue("add-item-meal-id"));

        setModalError(PICKER_ID, null);
        setBusy(saveItems, true);

        try {
            const mealPayload = {
                category,
                time: getValue("add-meal-time") || null,
                locale: getLocale(),
            };

            if (mealId) {
                await NutritionAPI.updateMeal(mealId, mealPayload);
            } else {
                const meal = await NutritionAPI.createMeal(mealPayload);
                mealId = meal.id;
                // If saving the products fails, retrying must not create a second meal.
                setValue("add-item-meal-id", String(mealId));
            }

            await NutritionAPI.createEntries(
                mealId,
                pendingMealItems.map((entry) => ({
                    product_id: entry.product.id,
                    amount: entry.amount,
                    unit: entry.unit,
                })),
                getLocale(),
            );

            pendingMealItems = [];
            existingMealItems = [];
            closeModal(PICKER_ID);
            emitNutritionChange("meals");
            await onRefresh();
        } catch (error) {
            setModalError(PICKER_ID, describeError(error));
        } finally {
            setBusy(saveItems, false);
        }
    });

    /* Edit entry */

    onClick(["close-edit-item"], () => closeModal(EDIT_ID));

    const saveEdit = document.getElementById("save-edit-item") as HTMLButtonElement | null;

    saveEdit?.addEventListener("click", async () => {
        const id = Number(getValue("edit-item-id"));
        const mealId = Number(getValue("edit-item-meal-id"));
        const unit = getValue("edit-item-unit") as NutritionUnit;
        const amount = parseNumber(getValue("edit-item-amount"));

        if (!Number.isFinite(amount) || amount <= 0 || amount > (MAX_AMOUNT[unit] ?? 5000)) {
            markInvalid("edit-item-amount", true);
            setModalError(EDIT_ID, nutrition_t("errors.amount", { max: MAX_AMOUNT[unit] ?? 5000, unit: unitLabel(unit) }));
            return;
        }

        if (!id || !mealId) return;

        markInvalid("edit-item-amount", false);
        setModalError(EDIT_ID, null);
        setBusy(saveEdit, true);

        try {
            await NutritionAPI.updateEntry(id, { meal_id: mealId, amount, unit, locale: getLocale() });
            closeModal(EDIT_ID);
            emitNutritionChange("meals");
            await onRefresh();
        } catch (error) {
            setModalError(EDIT_ID, describeError(error));
        } finally {
            setBusy(saveEdit, false);
        }
    });

    /* My product */

    const gramsField = document.getElementById("product-grams-per-unit-field");
    const syncGramsField = (): void => {
        if (gramsField) gramsField.hidden = getValue("product-unit") !== "pcs";
    };

    document.getElementById("product-unit")?.addEventListener("change", syncGramsField);

    onClick(["open-add-my-product"], () => {
        ["product-name", "product-brand", "product-kcal", "product-protein", "product-fat", "product-carbs", "product-fiber"]
            .forEach((id) => {
                setValue(id, "");
                markInvalid(id, false);
            });

        setValue("product-name", getValue("add-item-search").trim());
        setValue("product-grams-per-unit", "100");
        setValue("product-unit", "g");
        syncGramsField();

        const liquid = document.getElementById("product-is-liquid") as HTMLInputElement | null;
        if (liquid) liquid.checked = false;

        openModal(PRODUCT_ID, "#product-name");
    });

    onClick(["close-add-product"], () => closeModal(PRODUCT_ID));

    const saveProduct = document.getElementById("save-add-product") as HTMLButtonElement | null;

    saveProduct?.addEventListener("click", async () => {
        const name = getValue("product-name").trim();
        if (!name) {
            markInvalid("product-name", true);
            setModalError(PRODUCT_ID, nutrition_t("errors.nameRequired"));
            return;
        }
        markInvalid("product-name", false);

        const limits: Record<string, number> = {
            "product-kcal": 950,
            "product-protein": 100,
            "product-fat": 100,
            "product-carbs": 100,
            "product-fiber": 100,
        };

        const values: Record<string, number> = {};
        for (const [id, max] of Object.entries(limits)) {
            const raw = getValue(id).trim();
            const value = raw ? parseNumber(raw) : 0;
            const invalid = !Number.isFinite(value) || value < 0 || value > max;
            markInvalid(id, invalid);
            if (invalid) {
                setModalError(PRODUCT_ID, nutrition_t("errors.invalid_product"));
                return;
            }
            values[id] = value;
        }

        const unit = getValue("product-unit") as NutritionUnit;
        let gramsPerUnit = 1;
        if (unit === "pcs") {
            gramsPerUnit = parseNumber(getValue("product-grams-per-unit"));
            if (!Number.isFinite(gramsPerUnit) || gramsPerUnit <= 0 || gramsPerUnit > 5000) {
                markInvalid("product-grams-per-unit", true);
                setModalError(PRODUCT_ID, nutrition_t("errors.invalid_product"));
                return;
            }
        }
        markInvalid("product-grams-per-unit", false);

        setModalError(PRODUCT_ID, null);
        setBusy(saveProduct, true);

        try {
            const product = await NutritionAPI.createProduct({
                name,
                brand: getValue("product-brand").trim() || null,
                locale: getLocale(),
                kcal_per_100g: values["product-kcal"],
                protein_per_100g: values["product-protein"],
                fat_per_100g: values["product-fat"],
                carbs_per_100g: values["product-carbs"],
                fiber_per_100g: values["product-fiber"],
                liquid_ml_per_100g: (document.getElementById("product-is-liquid") as HTMLInputElement | null)?.checked ? 100 : 0,
                default_unit: unit,
                grams_per_unit: gramsPerUnit,
            });

            closeModal(PRODUCT_ID);
            setValue("add-item-search", "");
            setCatalogMode("mine");
            await loadCatalog();
            selectProduct(product);
        } catch (error) {
            setModalError(PRODUCT_ID, describeError(error));
        } finally {
            setBusy(saveProduct, false);
        }
    });
}
