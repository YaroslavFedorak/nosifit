const BASE_URL = "/api/nutrition";
async function request(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || "Something went wrong");
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
