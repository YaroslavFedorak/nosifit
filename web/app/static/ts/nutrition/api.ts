import type {
    EntryUpdatePayload,
    Meal,
    MealItemPayload,
    MealPayload,
    NutritionDay,
    NutritionDayDetails,
    NutritionHeatmapResponse,
    NutritionRecommendationResponse,
    Product,
    ProductListResponse,
    ProductPayload,
    WaterPayload,
    WaterResponse,
    WeightPayload,
    WeightResponse,
} from "./types.js";

const BASE_URL = "/api/nutrition";

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
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
    return data as T;
}

export const NutritionAPI = {
    getDay(locale = "uk"): Promise<NutritionDay> {
        return request<NutritionDay>(
            BASE_URL + "/day?locale=" + encodeURIComponent(locale),
        );
    },
    getDayDetails(date: string, locale = "uk"): Promise<NutritionDayDetails> {
        return request<NutritionDayDetails>(
            BASE_URL + "/day/" + date + "?locale=" + encodeURIComponent(locale),
        );
    },
    getRecommendations(): Promise<NutritionRecommendationResponse> {
        return request<NutritionRecommendationResponse>(BASE_URL + "/recommendations");
    },
    getProducts(query = "", locale = "uk"): Promise<ProductListResponse> {
        return request<ProductListResponse>(
            BASE_URL + "/products?q=" + encodeURIComponent(query) + "&locale=" + encodeURIComponent(locale),
        );
    },
    getRecentProducts(locale = "uk"): Promise<ProductListResponse> {
        return request<ProductListResponse>(BASE_URL + "/products/recent?locale=" + encodeURIComponent(locale));
    },
    getFavoriteProducts(locale = "uk"): Promise<ProductListResponse> {
        return request<ProductListResponse>(BASE_URL + "/products/favorites?locale=" + encodeURIComponent(locale));
    },
    getMyProducts(locale = "uk"): Promise<ProductListResponse> {
        return request<ProductListResponse>(BASE_URL + "/products/mine?locale=" + encodeURIComponent(locale));
    },
    getProduct(id: number, locale = "uk"): Promise<Product> {
        return request<Product>(BASE_URL + "/products/" + id + "?locale=" + encodeURIComponent(locale));
    },
    createProduct(data: ProductPayload): Promise<Product> {
        return request<Product>(BASE_URL + "/products", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateProduct(id: number, data: Partial<ProductPayload>): Promise<Product> {
        return request<Product>(BASE_URL + "/products/" + id, {
            method: "PATCH",
            body: JSON.stringify(data),
        });
    },
    deleteProduct(id: number): Promise<void> {
        return request<void>(BASE_URL + "/products/" + id, {
            method: "DELETE",
        });
    },
    setProductFavorite(id: number, favorite: boolean, locale = "uk"): Promise<Product> {
        return request<Product>(BASE_URL + "/products/" + id + "/favorite", {
            method: "POST",
            body: JSON.stringify({ favorite, locale }),
        });
    },
    createMeal(data: MealPayload): Promise<Meal> {
        return request<Meal>(BASE_URL + "/meals", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateMeal(id: number, data: MealPayload): Promise<Meal> {
        return request<Meal>(BASE_URL + "/meals/" + id, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteMeal(id: number): Promise<void> {
        return request<void>(BASE_URL + "/meals/" + id, {
            method: "DELETE",
        });
    },
    createEntry(data: MealItemPayload): Promise<{ id: number; status: string }> {
        return request(BASE_URL + "/entries", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },

    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use createEntry().
     */
    createItem(data: MealItemPayload | Record<string, unknown>): Promise<{ id: number; status: string }> {
        return request(BASE_URL + "/items", {
            method: "POST",
            body: JSON.stringify(data),
        });
    },
    updateEntry(id: number, data: EntryUpdatePayload): Promise<{ id: number; status: string }> {
        return request(BASE_URL + "/entries/" + id, {
            method: "PATCH",
            body: JSON.stringify(data),
        });
    },

    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use updateEntry().
     */
    updateItem(id: number, data: EntryUpdatePayload | Record<string, unknown>): Promise<{ id: number; status: string }> {
        return request(BASE_URL + "/items/" + id, {
            method: "PUT",
            body: JSON.stringify(data),
        });
    },
    deleteEntry(id: number): Promise<void> {
        return request<void>(BASE_URL + "/entries/" + id, {
            method: "DELETE",
        });
    },

    /**
     * Compatibility alias for legacy nutrition UI.
     * New code should use deleteEntry().
     */
    deleteItem(id: number): Promise<void> {
        return request<void>(BASE_URL + "/items/" + id, {
            method: "DELETE",
        });
    },
    getWeight(): Promise<WeightResponse> {
        return request<WeightResponse>(BASE_URL + "/weight");
    },

    updateWeight(weight: number): Promise<void> {
        return request<void>(BASE_URL + "/weight", {
            method: "POST",
            body: JSON.stringify({ weight }),
        });
    },
    getWater(): Promise<WaterResponse> {
        return request<WaterResponse>(BASE_URL + "/water");
    },

    addWater(amount: number): Promise<WaterResponse> {
        return request<WaterResponse>(BASE_URL + "/water", {
            method: "POST",
            body: JSON.stringify({ amount }),
        });
    },
    copyYesterday(): Promise<void> {
        return request<void>(BASE_URL + "/copy-yesterday", {
            method: "POST",
        });
    },
    getHeatmap(year: number): Promise<NutritionHeatmapResponse> {
        return request<NutritionHeatmapResponse>(BASE_URL + "/heatmap?year=" + year);
    },
};
