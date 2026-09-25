import {
    NutritionAPI,
} from "./api.js";


import type {
    WaterResponse,
} from "./types.js";


import {
    nutrition_t,
} from "../i18n/index.js";


const waterWidget =
    document.getElementById(
        "water-widget",
    ) as HTMLElement | null;


const waterCurrent =
    document.getElementById(
        "water-current",
    ) as HTMLElement | null;


const waterProgress =
    document.getElementById(
        "water-progress",
    ) as HTMLElement | null;


let currentWater = 0;
let recommendedWater = 0;


function updateWaterVisual(): void {
    if (
        !waterWidget ||
        !waterCurrent ||
        !waterProgress
    ) {
        return;
    }

    if (recommendedWater <= 0) {
        waterWidget.style.setProperty(
            "--fill",
            "0",
        );

        waterWidget.style.setProperty(
            "--overflow",
            "0",
        );

        waterWidget.classList.remove(
            "is-overflowing",
        );

        waterCurrent.textContent =
            currentWater.toFixed(1);

        waterProgress.textContent =
            nutrition_t(
                "water.recommendation_unavailable",
            );

        return;
    }

    const ratio =
        currentWater /
        recommendedWater;

    const fillPercent =
        Math.min(
            ratio,
            1,
        ) * 80;

    const overflowRatio =
        Math.min(
            Math.max(
                ratio - 1,
                0,
            ),
            1,
        );

    waterWidget.style.setProperty(
        "--fill",
        fillPercent.toFixed(1),
    );

    waterWidget.style.setProperty(
        "--overflow",
        overflowRatio.toFixed(2),
    );

    waterWidget.classList.toggle(
        "is-overflowing",
        ratio > 1,
    );

    waterCurrent.textContent =
        currentWater.toFixed(1);

    waterProgress.textContent =
        nutrition_t(
            "water.progress",
            {
                value:
                    Math.round(
                        ratio * 100,
                    ),
            },
        );
}


function applyWaterData(
    data: WaterResponse,
): void {
    currentWater =
        Number(
            data.amount ?? 0,
        );

    recommendedWater =
        Number(
            data.recommended ?? 0,
        );

    updateWaterVisual();
}


export async function loadWater(): Promise<void> {
    try {
        const data =
            await NutritionAPI.getWater();

        applyWaterData(
            data,
        );

    } catch (error) {
        console.error(
            "Failed to load water:",
            error,
        );
    }
}


document.addEventListener(
    "nutrition:water-updated",
    () => {
        void loadWater();
    },
);