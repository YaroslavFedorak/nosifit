import { NutritionAPIError } from "./errors.js";
const BASE_URL = "/api/nutrition";
async function request(url, options = {}) {
    let response;
    try {
        response = await fetch(url, {
            ...options,
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                ...(options.headers || {}),
            },
        });
    }
    catch {
        throw new NutritionAPIError("Network error", "network", 0);
    }
    // An expired session redirects to the login page (HTML, not JSON).
    if (response.redirected && new URL(response.url).pathname.startsWith("/auth/login")) {
        throw new NutritionAPIError("Session expired", "session_expired", 401);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new NutritionAPIError(data.error || "Request failed", data.code || (response.status === 401 ? "session_expired" : "unknown"), response.status);
    }
    return data;
}
export const NutritionAPI = {
    getDay(locale = "uk") {
        return request(BASE_URL + "/day?locale=" + encodeURIComponent(locale));
    },
    getDayDetails(date, locale = "uk") {
        return request(BASE_URL + "/day/" + date + "?locale=" + encodeURIComponent(locale));
    },
    getRecommendations() {
        return request(BASE_URL + "/recommendations");
    },
    getProducts(query = "", locale = "uk") {
        return request(BASE_URL + "/products?q=" + encodeURIComponent(query) + "&locale=" + encodeURIComponent(locale));
    },
    getRecentProducts(locale = "uk") {
        return request(BASE_URL + "/products/recent?locale=" + encodeURIComponent(locale));
    },
    getFavoriteProducts(locale = "uk") {
        return request(BASE_URL + "/products/favorites?locale=" + encodeURIComponent(locale));
    },
    getMyProducts(locale = "uk") {
        return request(BASE_URL + "/products/mine?locale=" + encodeURIComponent(locale));
    },
    getProduct(id, locale = "uk") {
        return request(BASE_URL + "/products/" + id + "?locale=" + encodeURIComponent(locale));
    },
    createProduct(data) {
        return request(BASE_URL + "/products", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateProduct(id, data) {
        return request(BASE_URL + "/products/" + id, {
            method: "PATCH",
            body: JSON.stringify(data),
        });
    },
    deleteProduct(id) {
        return request(BASE_URL + "/products/" + id, {
            method: "DELETE",
        });
    },
    setProductFavorite(id, favorite, locale = "uk") {
        return request(BASE_URL + "/products/" + id + "/favorite", {
            method: "POST",
            body: JSON.stringify({ favorite, locale }),
        });
    },
    createMeal(data) {
        return request(BASE_URL + "/meals", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateMeal(id, data) {
        return request(BASE_URL + "/meals/" + id, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteMeal(id) {
        return request(BASE_URL + "/meals/" + id, {
            method: "DELETE",
        });
    },
    createEntries(mealId, items, locale = "uk") {
        return request(BASE_URL + "/entries/bulk", {
            method: "POST",
            body: JSON.stringify({ meal_id: mealId, items, locale }),
        });
    },
    createEntry(data) {
        return request(BASE_URL + "/entries", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use createEntry().
     */
    createItem(data) {
        return request(BASE_URL + "/items", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateEntry(id, data) {
        return request(BASE_URL + "/entries/" + id, {
            method: "PATCH",
            body: JSON.stringify(data),
        });
    },
    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use updateEntry().
     */
    updateItem(id, data) {
        return request(BASE_URL + "/items/" + id, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteEntry(id) {
        return request(BASE_URL + "/entries/" + id, {
            method: "DELETE",
        });
    },
    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use deleteEntry().
     */
    deleteItem(id) {
        return request(BASE_URL + "/items/" + id, {
            method: "DELETE",
        });
    },
    getWeight() {
        return request(BASE_URL + "/weight");
    },
    updateWeight(weight) {
        return request(BASE_URL + "/weight", {
            method: "POST",
            body: JSON.stringify({ weight }),
        });
    },
    getWater() {
        return request(BASE_URL + "/water");
    },
    /** Positive adds, negative subtracts (fixing a mistaken entry). */
    addWater(amount) {
        return request(BASE_URL + "/water", {
            method: "POST",
            body: JSON.stringify({ amount }),
        });
    },
    copyYesterday() {
        return request(BASE_URL + "/copy-yesterday", {
            method: "POST",
        });
    },
    getHeatmap(year) {
        return request(BASE_URL + "/heatmap?year=" + year);
    },
};
