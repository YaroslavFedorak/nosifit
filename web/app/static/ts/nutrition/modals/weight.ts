import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
    openModal,
} from "./modal.js";


type RefreshCallback = () => void | Promise<void>;


function getInputValue(id: string): string {
    const element = document.getElementById(id) as HTMLInputElement | null;

    return element?.value ?? "";
}


function setInputValue(
    id: string,
    value: string,
): void {
    const element = document.getElementById(id) as HTMLInputElement | null;

    if (element) {
        element.value = value;
    }
}


export function setupWeightModal(
    onRefresh: RefreshCallback,
): void {
    document.getElementById(
        "open-update-weight"
    )?.addEventListener(
        "click",
        () => {
            setInputValue(
                "update-weight-value",
                ""
            );

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
                getInputValue(
                    "update-weight-value"
                )
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

            await onRefresh();
        }
    );
}