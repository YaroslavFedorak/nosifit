/**
 * Food picker + "my product" + edit-entry modals.
 * Shared by the Nutrition page and the Dashboard.
 */
import { NutritionAPI } from "../api.js";
import { formatAmount, mealCategoryLabel, normalizeMealCategory, suggestMealCategory, unitLabel, } from "../categories.js";
import { describeError } from "../errors.js";
import { setupBarcodeScanner } from "./barcode.js";
import { getLocale, nutrition_t } from "../../i18n/index.js";
import { closeModal, emitNutritionChange, getValue, markInvalid, onClick, openModal, parseNumber, setBusy, setModalError, setValue, } from "./modal.js";
const PICKER_ID = "modal-add-item";
const PRODUCT_ID = "modal-add-product";
const EDIT_ID = "modal-edit-item";
const MAX_AMOUNT = { g: 5000, ml: 5000, pcs: 100 };
const STAR_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.8l2.55 5.16 5.7.83-4.13 4.03.98 5.69L12 16.82 6.9 19.51l.98-5.69L3.75 9.79l5.7-.83L12 3.8z"></path></svg>';
const REMOVE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>';
const PENCIL_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/></svg>';
const CHECK_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>';
let selectedProduct = null;
let pendingMealItems = [];
let existingMealItems = [];
let catalogMode = "all";
let catalogProducts = { favorites: [], recent: [], mine: [], all: [] };
let catalogSearchRequest = 0;
let searchDebounce;
let editingProduct = null;
let refreshAfterChange = () => undefined;
function formatCalories(value) {
    return String(Math.round(Number(value ?? 0)));
}
function formatMacro(value) {
    const number = Number(value ?? 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
}
function defaultAmount(unit) {
    return unit === "pcs" ? "1" : "100";
}
/* ---------- Rendering ---------- */
function createProductRow(product) {
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
    if (product.is_own) {
        const badge = document.createElement("span");
        badge.className = "nf-product-own-badge";
        badge.textContent = nutrition_t("catalog.ownBadge");
        name.appendChild(badge);
    }
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
        }
        catch (error) {
            setModalError(PICKER_ID, describeError(error));
        }
        finally {
            favorite.disabled = false;
        }
    });
    wrapper.append(select, favorite);
    if (product.is_own) {
        wrapper.classList.add("nf-product--own");
        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "nf-product-edit";
        edit.innerHTML = PENCIL_ICON;
        const editLabel = `${nutrition_t("catalog.editMyProductTitle")}: ${product.name}`;
        edit.setAttribute("aria-label", editLabel);
        edit.title = nutrition_t("catalog.editMyProductTitle");
        edit.addEventListener("click", (event) => {
            event.stopPropagation();
            openProductModal(product);
        });
        wrapper.appendChild(edit);
    }
    return wrapper;
}
function emptyTextFor(elementId) {
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
function renderProductList(elementId, products) {
    const element = document.getElementById(elementId);
    if (!element)
        return;
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
function refreshSelectionState() {
    document
        .querySelectorAll(`#${PICKER_ID} .nf-product-select`)
        .forEach((button) => {
        button.setAttribute("aria-pressed", String(Number(button.dataset.productId) === selectedProduct?.id));
    });
    const add = document.getElementById("add-item-to-meal");
    if (add)
        add.disabled = selectedProduct === null;
}
function renderSelectedProduct() {
    const element = document.getElementById("selected-product");
    if (!element)
        return;
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
function createPendingRow(name, amount, options) {
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
    }
    else {
        const status = document.createElement("span");
        status.className = "nf-pending-status";
        status.innerHTML = CHECK_ICON;
        status.title = nutrition_t("catalog.alreadyAdded");
        status.setAttribute("aria-label", nutrition_t("catalog.alreadyAdded"));
        row.appendChild(status);
    }
    return row;
}
function pendingCalories() {
    return pendingMealItems.reduce((sum, entry) => {
        const grams = entry.unit === "pcs"
            ? entry.amount * Number(entry.product.grams_per_unit || 0)
            : entry.unit === "ml"
                ? entry.amount * Number(entry.product.grams_per_unit || 1)
                : entry.amount;
        return sum + (Number(entry.product.kcal_per_100g || 0) * grams) / 100;
    }, 0);
}
function renderPendingMealItems() {
    const container = document.getElementById("pending-meal-items");
    const empty = document.getElementById("pending-meal-items-empty");
    const total = document.getElementById("pending-meal-total");
    if (!container || !empty)
        return;
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
        container.appendChild(createPendingRow(item.name, formatAmount(item.amount, item.unit), { existing: true }));
    });
    pendingMealItems.forEach((entry, index) => {
        container.appendChild(createPendingRow(entry.product.name, formatAmount(entry.amount, entry.unit), {
            existing: false,
            onRemove: () => {
                pendingMealItems.splice(index, 1);
                renderPendingMealItems();
            },
        }));
    });
    container.scrollTop = container.scrollHeight;
}
/* ---------- Selection ---------- */
function selectProduct(product) {
    selectedProduct = product;
    setValue("add-item-unit", product.default_unit);
    setValue("add-item-amount", defaultAmount(product.default_unit));
    markInvalid("add-item-amount", false);
    setModalError(PICKER_ID, null);
    renderSelectedProduct();
    const amount = document.getElementById("add-item-amount");
    if (amount && window.matchMedia("(pointer: fine)").matches) {
        amount.focus();
        amount.select();
    }
}
/** Moves the selected product into the meal. Returns false when the amount is invalid. */
function queueSelectedProduct() {
    if (!selectedProduct) {
        setModalError(PICKER_ID, nutrition_t("errors.selectProduct"));
        return false;
    }
    const unit = (getValue("add-item-unit") || selectedProduct.default_unit);
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
    const search = document.getElementById("add-item-search");
    if (search && search.value && window.matchMedia("(pointer: fine)").matches) {
        search.select();
        search.focus();
    }
    return true;
}
/* ---------- Catalog ---------- */
function setCatalogMode(mode) {
    catalogMode = mode;
    applyCatalogVisibility();
    document.querySelectorAll(`#${PICKER_ID} [data-catalog-sort]`).forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.catalogSort === catalogMode));
    });
}
function applyCatalogVisibility() {
    const searching = getValue("add-item-search").trim().length > 0;
    document.querySelectorAll(`#${PICKER_ID} [data-catalog-section]`).forEach((section) => {
        const sectionMode = section.dataset.catalogSection;
        section.hidden = searching ? sectionMode !== "search" : sectionMode !== catalogMode;
    });
}
async function loadCatalog() {
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
    }
    catch (error) {
        setModalError(PICKER_ID, describeError(error));
    }
}
async function searchCatalog(query) {
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
            if (requestId !== catalogSearchRequest)
                return;
            renderProductList("product-search-results", response.products);
            refreshSelectionState();
        }
        catch (error) {
            if (requestId === catalogSearchRequest) {
                renderProductList("product-search-results", []);
                setModalError(PICKER_ID, describeError(error));
            }
        }
        return;
    }
    const needle = normalizedQuery.toLocaleLowerCase();
    const products = catalogProducts[catalogMode].filter((product) => `${product.name} ${product.brand ?? ""}`.toLocaleLowerCase().includes(needle));
    if (requestId === catalogSearchRequest) {
        renderProductList("product-search-results", products);
        refreshSelectionState();
    }
}
/* ---------- Public API ---------- */
/** Opens the picker. `mealId = 0` creates a new meal on save. */
export function openAddItemModal(mealId, meal) {
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
export async function openEditItemModal(item) {
    const meal = document.getElementById("edit-item-meal-id");
    if (!meal)
        return;
    setValue("edit-item-id", String(item.id));
    setValue("edit-item-product", item.name);
    setValue("edit-item-amount", String(item.amount ?? item.weight ?? 100));
    setValue("edit-item-unit", item.unit ?? "g");
    markInvalid("edit-item-amount", false);
    meal.innerHTML = "";
    openModal(EDIT_ID, "#edit-item-amount");
    const openProduct = document.getElementById("edit-item-open-product");
    if (openProduct) {
        openProduct.hidden = true;
        openProduct.onclick = null;
        if (item.product_id) {
            NutritionAPI.getProduct(item.product_id, getLocale())
                .then((product) => {
                if (!product.is_own)
                    return;
                openProduct.hidden = false;
                openProduct.onclick = () => openProductModal(product);
            })
                .catch(() => undefined);
        }
    }
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
        const currentMeal = day.meals.find((entry) => entry.items?.some((entryItem) => entryItem.id === item.id));
        if (currentMeal)
            meal.value = String(currentMeal.id);
    }
    catch (error) {
        setModalError(EDIT_ID, describeError(error));
    }
}
export function setupItemModals(onRefresh) {
    refreshAfterChange = onRefresh;
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
        setValue("add-item-amount", defaultAmount(getValue("add-item-unit")));
    });
    document.querySelectorAll(`#${PICKER_ID} [data-catalog-sort]`).forEach((button) => {
        button.addEventListener("click", () => {
            const mode = button.dataset.catalogSort;
            if (!mode)
                return;
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
    const saveItems = document.getElementById("save-add-item");
    saveItems?.addEventListener("click", async () => {
        // A product that is selected but not yet added is clearly meant to be saved too.
        if (selectedProduct && !queueSelectedProduct())
            return;
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
            }
            else {
                const meal = await NutritionAPI.createMeal(mealPayload);
                mealId = meal.id;
                // If saving the products fails, retrying must not create a second meal.
                setValue("add-item-meal-id", String(mealId));
            }
            await NutritionAPI.createEntries(mealId, pendingMealItems.map((entry) => ({
                product_id: entry.product.id,
                amount: entry.amount,
                unit: entry.unit,
            })), getLocale());
            pendingMealItems = [];
            existingMealItems = [];
            closeModal(PICKER_ID);
            emitNutritionChange("meals");
            await onRefresh();
        }
        catch (error) {
            setModalError(PICKER_ID, describeError(error));
        }
        finally {
            setBusy(saveItems, false);
        }
    });
    /* Edit entry */
    onClick(["close-edit-item"], () => closeModal(EDIT_ID));
    const saveEdit = document.getElementById("save-edit-item");
    saveEdit?.addEventListener("click", async () => {
        const id = Number(getValue("edit-item-id"));
        const mealId = Number(getValue("edit-item-meal-id"));
        const unit = getValue("edit-item-unit");
        const amount = parseNumber(getValue("edit-item-amount"));
        if (!Number.isFinite(amount) || amount <= 0 || amount > (MAX_AMOUNT[unit] ?? 5000)) {
            markInvalid("edit-item-amount", true);
            setModalError(EDIT_ID, nutrition_t("errors.amount", { max: MAX_AMOUNT[unit] ?? 5000, unit: unitLabel(unit) }));
            return;
        }
        if (!id || !mealId)
            return;
        markInvalid("edit-item-amount", false);
        setModalError(EDIT_ID, null);
        setBusy(saveEdit, true);
        try {
            await NutritionAPI.updateEntry(id, { meal_id: mealId, amount, unit, locale: getLocale() });
            closeModal(EDIT_ID);
            emitNutritionChange("meals");
            await onRefresh();
        }
        catch (error) {
            setModalError(EDIT_ID, describeError(error));
        }
        finally {
            setBusy(saveEdit, false);
        }
    });
    /* My product */
    const gramsField = document.getElementById("product-grams-per-unit-field");
    const syncGramsField = () => {
        if (gramsField)
            gramsField.hidden = getValue("product-unit") !== "pcs";
    };
    document.getElementById("product-unit")?.addEventListener("change", syncGramsField);
    onClick(["open-add-my-product"], () => openProductModal(null));
    setupBarcodeScanner({
        onProduct: async (product) => {
            // The scanned product becomes the selection, like a clicked row;
            // an imported one is in "My products", where it can be edited.
            setValue("add-item-search", "");
            if (product.is_own)
                setCatalogMode("mine");
            applyCatalogVisibility();
            selectProduct(product);
            await loadCatalog();
        },
        onCreateOwn: (prefill) => openProductModal(null, prefill),
    });
    onClick(["close-add-product"], () => closeModal(PRODUCT_ID));
    const saveProduct = document.getElementById("save-add-product");
    saveProduct?.addEventListener("click", async () => {
        const name = getValue("product-name").trim();
        if (!name) {
            markInvalid("product-name", true);
            setModalError(PRODUCT_ID, nutrition_t("errors.nameRequired"));
            return;
        }
        markInvalid("product-name", false);
        const limits = {
            "product-kcal": 950,
            "product-protein": 100,
            "product-fat": 100,
            "product-carbs": 100,
            "product-fiber": 100,
            "product-sugar": 100,
        };
        // Fiber and sugar may be unknown: an empty field is sent as null
        // ("unknown"), never as 0.
        const optional = new Set(["product-fiber", "product-sugar"]);
        // From a barcode scan the macros must come from the label: a blank
        // field is a value the scan did not have, not a 0.
        const barcode = getValue("product-barcode").trim();
        const required = barcode && !editingProduct
            ? new Set(["product-kcal", "product-protein", "product-fat", "product-carbs"])
            : new Set();
        const values = {};
        for (const [id, max] of Object.entries(limits)) {
            const raw = getValue(id).trim();
            if (!raw && optional.has(id)) {
                markInvalid(id, false);
                values[id] = null;
                continue;
            }
            if (!raw && required.has(id)) {
                markInvalid(id, true);
                setModalError(PRODUCT_ID, nutrition_t("errors.invalid_product"));
                return;
            }
            const value = raw ? parseNumber(raw) : 0;
            const invalid = !Number.isFinite(value) || value < 0 || value > max;
            markInvalid(id, invalid);
            if (invalid) {
                setModalError(PRODUCT_ID, nutrition_t("errors.invalid_product"));
                return;
            }
            values[id] = value;
        }
        const unit = getValue("product-unit");
        // Keep the stored density (e.g. milk 1.03 g/ml) unless the unit changes.
        let gramsPerUnit = editingProduct && editingProduct.default_unit === unit && unit !== "pcs"
            ? Number(editingProduct.grams_per_unit || 1)
            : 1;
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
        const payload = {
            name,
            brand: getValue("product-brand").trim() || null,
            // Only when created from a scan: the product is then found by it.
            ...(barcode && !editingProduct ? { barcode } : {}),
            locale: getLocale(),
            kcal_per_100g: values["product-kcal"] ?? 0,
            protein_per_100g: values["product-protein"] ?? 0,
            fat_per_100g: values["product-fat"] ?? 0,
            carbs_per_100g: values["product-carbs"] ?? 0,
            fiber_per_100g: values["product-fiber"],
            sugar_per_100g: values["product-sugar"],
            liquid_ml_per_100g: document.getElementById("product-is-liquid")?.checked ? 100 : 0,
            default_unit: unit,
            grams_per_unit: gramsPerUnit,
        };
        try {
            if (editingProduct) {
                const updated = await NutritionAPI.updateProduct(editingProduct.id, payload);
                closeModal(PRODUCT_ID);
                await afterProductChanged(updated, null);
            }
            else {
                const product = await NutritionAPI.createProduct(payload);
                closeModal(PRODUCT_ID);
                setValue("add-item-search", "");
                setCatalogMode("mine");
                await loadCatalog();
                selectProduct(product);
            }
        }
        catch (error) {
            setModalError(PRODUCT_ID, describeError(error));
        }
        finally {
            setBusy(saveProduct, false);
        }
    });
    const deleteProduct = document.getElementById("delete-my-product");
    let deleteTimer;
    const disarmDelete = () => {
        window.clearTimeout(deleteTimer);
        if (!deleteProduct)
            return;
        deleteProduct.classList.remove("is-confirming");
        deleteProduct.textContent = deleteProduct.dataset.label ?? nutrition_t("catalog.deleteProduct");
    };
    deleteProduct?.addEventListener("click", async () => {
        if (!editingProduct)
            return;
        // Two-step: first click arms, second (within 3 s) deletes.
        if (!deleteProduct.classList.contains("is-confirming")) {
            deleteProduct.classList.add("is-confirming");
            deleteProduct.textContent = deleteProduct.dataset.labelConfirm ?? nutrition_t("actions.confirmDelete");
            deleteTimer = window.setTimeout(disarmDelete, 3000);
            return;
        }
        disarmDelete();
        setBusy(deleteProduct, true);
        try {
            const removed = editingProduct;
            await NutritionAPI.deleteProduct(removed.id);
            closeModal(PRODUCT_ID);
            await afterProductChanged(null, removed.id);
        }
        catch (error) {
            setModalError(PRODUCT_ID, describeError(error));
        }
        finally {
            setBusy(deleteProduct, false);
        }
    });
    document.getElementById(PRODUCT_ID)?.addEventListener("nf-modal:closed", () => {
        disarmDelete();
        editingProduct = null;
    });
}
/**
 * Opens "My product" empty (create), filled with an own product (edit) or
 * prefilled from a barcode scan (create; missing values stay empty).
 */
export function openProductModal(product, prefill) {
    editingProduct = product;
    const scanned = prefill?.values ?? {};
    const fields = [
        ["product-name", product ? product.name : prefill ? (prefill.name ?? "") : getValue("add-item-search").trim()],
        ["product-brand", product?.brand ?? prefill?.brand ?? ""],
        ["product-kcal", product ? product.kcal_per_100g : scanned.kcal_per_100g],
        ["product-protein", product ? product.protein_per_100g : scanned.protein_per_100g],
        ["product-fat", product ? product.fat_per_100g : scanned.fat_per_100g],
        ["product-carbs", product ? product.carbs_per_100g : scanned.carbs_per_100g],
        ["product-fiber", product ? product.fiber_per_100g : scanned.fiber_per_100g],
        ["product-sugar", product ? product.sugar_per_100g : scanned.sugar_per_100g],
    ];
    fields.forEach(([id, value]) => {
        setValue(id, value === null || value === undefined ? "" : String(value));
        markInvalid(id, false);
    });
    setValue("product-barcode", product ? "" : (prefill?.barcode ?? ""));
    const unit = product?.default_unit ?? prefill?.unit ?? "g";
    setValue("product-unit", unit);
    setValue("product-grams-per-unit", unit === "pcs" ? String(product?.grams_per_unit ?? 100) : "100");
    markInvalid("product-grams-per-unit", false);
    const gramsField = document.getElementById("product-grams-per-unit-field");
    if (gramsField)
        gramsField.hidden = unit !== "pcs";
    const liquid = document.getElementById("product-is-liquid");
    if (liquid)
        liquid.checked = Number(product?.liquid_ml_per_100g ?? 0) > 0;
    const title = document.getElementById("add-product-title");
    if (title) {
        title.textContent = product
            ? (title.dataset.titleEdit ?? nutrition_t("catalog.editMyProductTitle"))
            : (title.dataset.titleCreate ?? nutrition_t("catalog.myProductTitle"));
    }
    const save = document.getElementById("save-add-product");
    if (save) {
        save.textContent = product
            ? (save.dataset.labelEdit ?? nutrition_t("actions.save"))
            : (save.dataset.labelCreate ?? nutrition_t("actions.create"));
    }
    const remove = document.getElementById("delete-my-product");
    if (remove)
        remove.hidden = !product;
    const hint = document.getElementById("product-edit-hint");
    if (hint)
        hint.hidden = !product;
    openModal(PRODUCT_ID, "#product-name");
}
/** Keeps the picker, pending items and the meal list in sync after edit/delete. */
async function afterProductChanged(updated, deletedId) {
    if (updated) {
        pendingMealItems = pendingMealItems.map((entry) => entry.product.id === updated.id ? { ...entry, product: updated } : entry);
        if (selectedProduct?.id === updated.id)
            selectedProduct = updated;
        const entryName = document.getElementById("edit-item-product");
        if (entryName && document.getElementById(EDIT_ID)?.classList.contains("open")) {
            entryName.value = updated.name;
        }
    }
    if (deletedId !== null) {
        pendingMealItems = pendingMealItems.filter((entry) => entry.product.id !== deletedId);
        if (selectedProduct?.id === deletedId)
            selectedProduct = null;
        const openProduct = document.getElementById("edit-item-open-product");
        if (openProduct)
            openProduct.hidden = true;
    }
    if (document.getElementById(PICKER_ID)?.classList.contains("open")) {
        renderSelectedProduct();
        renderPendingMealItems();
        await loadCatalog();
        if (getValue("add-item-search").trim()) {
            await searchCatalog(getValue("add-item-search"));
        }
    }
    // Logged entries were recalculated on the server.
    emitNutritionChange("meals");
    await refreshAfterChange();
}
