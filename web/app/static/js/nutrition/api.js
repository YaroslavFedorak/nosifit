const BASE_URL = "/api/nutrition";
async function request(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Something went wrong");
    }
    return data;
}
export const NutritionAPI = {
    getDay() {
        return request(`${BASE_URL}/day`);
    },
    getRecommendations() {
        return request(`${BASE_URL}/recommendations`);
    },
    createMeal(data) {
        return request(`${BASE_URL}/meals`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateMeal(id, data) {
        return request(`${BASE_URL}/meals/${id}`, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteMeal(id) {
        return request(`${BASE_URL}/meals/${id}`, {
            method: "DELETE",
        });
    },
    createItem(data) {
        return request(`${BASE_URL}/items`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateItem(id, data) {
        return request(`${BASE_URL}/items/${id}`, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteItem(id) {
        return request(`${BASE_URL}/items/${id}`, {
            method: "DELETE",
        });
    },
    updateWeight(weight) {
        const data = {
            weight,
        };
        return request(`${BASE_URL}/weight`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    addWater(amount) {
        const data = {
            amount,
        };
        return request(`${BASE_URL}/water`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    copyYesterday() {
        return request(`${BASE_URL}/copy-yesterday`, {
            method: "POST",
        });
    },
    getHeatmap(year) {
        return request(`${BASE_URL}/heatmap?year=${year}`);
    },
};
