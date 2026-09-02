import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
    openModal,
} from "./modal.js";


export function setupWaterModal(
    onRefresh,
) {
    document.getElementById(
        "open-water-modal"
    )?.addEventListener(
        "click",
        () => {
            document.getElementById(
                "water-amount"
            ).value = "";

            openModal(
                "modal-water"
            );
        }
    );


    document.getElementById(
        "close-water-modal"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-water"
            );
        }
    );


    document.getElementById(
        "save-water"
    )?.addEventListener(
        "click",
        async () => {
            const amount = Number(
                document.getElementById(
                    "water-amount"
                ).value || 0
            );

            if (!amount || amount <= 0) {
                return;
            }

            await NutritionAPI.addWater(
                amount
            );

            closeModal(
                "modal-water"
            );

            onRefresh();
        }
    );
}