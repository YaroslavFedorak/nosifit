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
    setupNutritionHeatmapModals,
} from "./modals/heatmap.js";


import {
    initializeNutritionHeatmap,
} from "./heatmap.js";


import {
    loadNutritionRecommendations,
} from "./recommendations.js";


import {
    loadWater,
} from "./water.js";


import {
    loadWeight,
} from "./weight.js";


import {
    getLocale,
    loadTranslations,
} from "../i18n/index.js";


import {
    ICONS,
} from "../icons/index.js";


function initNutritionIcons(): void {
    const weightIcon =
        document.querySelector(
            '[data-icon="weight"]',
        );

    const waterIcon =
        document.querySelector(
            '[data-icon="glass_water"]',
        );

    if (weightIcon) {
        weightIcon.innerHTML =
            ICONS.weight;
    }

    if (waterIcon) {
        waterIcon.innerHTML =
            ICONS.glass_water;
    }
}


function setTodayDate(): void {
    const element =
        document.getElementById(
            "current-date",
        );

    if (!element) {
        return;
    }

    const today =
        new Date();

    element.textContent =
        today.toLocaleDateString(
            getLocale(),
            {
                weekday: "long",
                day: "numeric",
                month: "long",
            },
        );
}


async function loadNutritionDay(): Promise<void> {
    try {
        const data =
            await NutritionAPI.getDay();

        renderBalance(
            data,
        );

        renderMeals(
            data.meals,
            loadNutritionDay,
        );

        await loadNutritionRecommendations();

        document.dispatchEvent(
            new CustomEvent(
                "nutrition:heatmap-reload",
            ),
        );
    } catch (error) {
        console.error(
            "Failed to load nutrition data:",
            error,
        );
    }
}


function initializeNutritionPage(): void {
    initNutritionIcons();
    setTodayDate();

    setupNutritionHeatmapModals();

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

    initializeNutritionHeatmap();

    void loadWater();
    void loadWeight();
    void loadNutritionDay();
}


async function startNutritionPage(): Promise<void> {
    try {
        await loadTranslations(
            "nutrition",
        );

        initializeNutritionPage();
    } catch (error) {
        console.error(
            "Failed to initialize nutrition translations:",
            error,
        );

        initializeNutritionPage();
    }
}


document.addEventListener(
    "DOMContentLoaded",
    () => {
        void startNutritionPage();
    },
);