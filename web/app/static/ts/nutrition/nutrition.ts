import {
    NutritionAPI,
} from "./api.js";

import {
    renderBalance,
} from "./ui/balance.js";

import {
    renderMeals,
} from "./ui/meals.js";

import {
    setupMealModals,
} from "./modals/meals.js";

import {
    setupItemModals,
} from "./modals/items.js";

import {
    setupWaterModal,
} from "./modals/water.js";

import {
    setupWeightModal,
} from "./modals/weight.js";

import {
    loadNutritionRecommendations,
} from "./recommendations.js";

function setTodayDate(): void {
    const element =
        document.getElementById(
            "current-date",
        );

    if (!element) {
        return;
    }

    const today = new Date();

    element.textContent =
        today.toLocaleDateString(
            "uk-UA",
            {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
            },
        );
}

async function loadNutritionDay(): Promise<void> {
    try {
        const data =
            await NutritionAPI.getDay();

        renderBalance(data);

        renderMeals(
            data.meals,
            loadNutritionDay,
        );

        await loadNutritionRecommendations();

    } catch (error) {
        console.error(
            "Failed to load nutrition data:",
            error,
        );
    }
}

function initializeNutritionPage(): void {
    setTodayDate();

    setupMealModals(
        loadNutritionDay,
    );

    setupItemModals(
        loadNutritionDay,
    );

    setupWaterModal(
        loadNutritionDay,
    );

    setupWeightModal(
        loadNutritionDay,
    );

    void loadNutritionDay();
}

document.addEventListener(
    "DOMContentLoaded",
    initializeNutritionPage,
);