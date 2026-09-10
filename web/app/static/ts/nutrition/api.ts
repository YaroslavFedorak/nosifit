import type {
    Meal,
    MealItem,
    MealItemPayload,
    MealPayload,
    NutritionDay,
    NutritionRecommendationResponse,
    WaterPayload,
    WaterResponse,
    WeightPayload,
    WeightResponse,
} from "./types.js";


const BASE_URL = "/api/nutrition";


async function request<T>(
    url: string,
    options: RequestInit = {},
): Promise<T> {
    const response = await fetch(
        url,
        {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            },
            ...options,
        },
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || "Something went wrong",
        );
    }

    return data as T;
}


export const NutritionAPI = {
    getDay(): Promise<NutritionDay> {
        return request<NutritionDay>(
            `${BASE_URL}/day`,
        );
    },


    getRecommendations(): Promise<NutritionRecommendationResponse> {
        return request<NutritionRecommendationResponse>(
            `${BASE_URL}/recommendations`,
        );
    },


    getWater(): Promise<WaterResponse> {
        return request<WaterResponse>(
            `${BASE_URL}/water`,
        );
    },


    getWeight(): Promise<WeightResponse> {
        return request<WeightResponse>(
            `${BASE_URL}/weight`,
        );
    },


    createMeal(
        data: MealPayload,
    ): Promise<Meal> {
        return request<Meal>(
            `${BASE_URL}/meals`,
            {
                method: "POST",
                body: JSON.stringify(data),
            },
        );
    },


    updateMeal(
        id: number,
        data: MealPayload,
    ): Promise<Meal> {
        return request<Meal>(
            `${BASE_URL}/meals/${id}`,
            {
                method: "PUT",
                body: JSON.stringify(data),
            },
        );
    },


    deleteMeal(
        id: number,
    ): Promise<void> {
        return request<void>(
            `${BASE_URL}/meals/${id}`,
            {
                method: "DELETE",
            },
        );
    },


    createItem(
        data: MealItemPayload,
    ): Promise<MealItem> {
        return request<MealItem>(
            `${BASE_URL}/items`,
            {
                method: "POST",
                body: JSON.stringify(data),
            },
        );
    },


    updateItem(
        id: number,
        data: Partial<MealItemPayload>,
    ): Promise<MealItem> {
        return request<MealItem>(
            `${BASE_URL}/items/${id}`,
            {
                method: "PUT",
                body: JSON.stringify(data),
            },
        );
    },


    deleteItem(
        id: number,
    ): Promise<void> {
        return request<void>(
            `${BASE_URL}/items/${id}`,
            {
                method: "DELETE",
            },
        );
    },


    updateWeight(
        weight: number,
    ): Promise<void> {
        const data: WeightPayload = {
            weight,
        };

        return request<void>(
            `${BASE_URL}/weight`,
            {
                method: "POST",
                body: JSON.stringify(data),
            },
        );
    },


    addWater(
        amount: number,
    ): Promise<WaterResponse> {
        const data: WaterPayload = {
            amount,
        };

        return request<WaterResponse>(
            `${BASE_URL}/water`,
            {
                method: "POST",
                body: JSON.stringify(data),
            },
        );
    },


    copyYesterday(): Promise<void> {
        return request<void>(
            `${BASE_URL}/copy-yesterday`,
            {
                method: "POST",
            },
        );
    },


    getHeatmap(
        year: number,
    ): Promise<unknown> {
        return request<unknown>(
            `${BASE_URL}/heatmap?year=${year}`,
        );
    },
};