import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
    openModal,
} from "./modal.js";


export function setupWeightModal(
    onRefresh,
) {
    document.getElementById(
        "open-update-weight"
    )?.addEventListener(
        "click",
        () => {
            document.getElementById(
                "update-weight-value"
            ).value = "";

            openModal(
                "modal-update-weight"
            );
        }
    );

    document.getElementById(
        "close-update-weight"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-update-weight"
            );
        }
    );

    document.getElementById(
        "save-update-weight"
    )?.addEventListener(
        "click",
        async () => {
            const weight = Number(
                document.getElementById(
                    "update-weight-value"
                ).value
            );

            if (!weight || weight <= 0) {
                return;
            }

            await NutritionAPI.updateWeight(
                weight
            );

            closeModal(
                "modal-update-weight"
            );

            onRefresh();
        }
    );
}