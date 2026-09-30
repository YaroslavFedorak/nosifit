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


export function setupMealModals(
    onRefresh: RefreshCallback,
): void {
    document.getElementById(
        "close-edit-meal"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-edit-meal"
            );
        }
    );

    document.getElementById(
        "save-edit-meal"
    )?.addEventListener(
        "click",
        async () => {
            const id =
                getInputValue(
                    "edit-meal-id"
                );

            const name =
                getInputValue(
                    "edit-meal-name"
                ).trim();

            if (!id || !name) {
                return;
            }

            await NutritionAPI.updateMeal(
                Number(id),
                {
                    name,

                    category:
                        getInputValue(
                            "edit-meal-category"
                        ),

                    time:
                        getInputValue(
                            "edit-meal-time"
                        ) || null,
                }
            );

            closeModal(
                "modal-edit-meal"
            );

            await onRefresh();
        }
    );
}