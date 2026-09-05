import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
} from "./modal.js";


type RefreshCallback = () => void | Promise<void>;


function getInputValue(id: string): string {
    const element = document.getElementById(id) as HTMLInputElement | null;

    return element?.value ?? "";
}


function getNumber(id: string): number {
    return Number(
        getInputValue(id) || 0
    );
}


export function setupItemModals(
    onRefresh: RefreshCallback,
): void {
    document.getElementById(
        "close-add-item"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-add-item"
            );
        }
    );

    document.getElementById(
        "save-add-item"
    )?.addEventListener(
        "click",
        async () => {
            const name =
                getInputValue(
                    "add-item-name"
                ).trim();

            if (!name) {
                return;
            }

            await NutritionAPI.createItem({
                meal_id: getNumber(
                    "add-item-meal-id"
                ),

                name,

                calories: getNumber(
                    "add-item-kcal"
                ),

                protein: getNumber(
                    "add-item-protein"
                ),

                fat: getNumber(
                    "add-item-fat"
                ),

                carbs: getNumber(
                    "add-item-carb"
                ),
            });

            closeModal(
                "modal-add-item"
            );

            await onRefresh();
        }
    );

    document.getElementById(
        "close-edit-item"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-edit-item"
            );
        }
    );

    document.getElementById(
        "save-edit-item"
    )?.addEventListener(
        "click",
        async () => {
            const id =
                getInputValue(
                    "edit-item-id"
                );

            const name =
                getInputValue(
                    "edit-item-name"
                ).trim();

            if (!id || !name) {
                return;
            }

            await NutritionAPI.updateItem(
                Number(id),
                {
                    name,

                    calories: getNumber(
                        "edit-item-kcal"
                    ),

                    protein: getNumber(
                        "edit-item-protein"
                    ),

                    fat: getNumber(
                        "edit-item-fat"
                    ),

                    carbs: getNumber(
                        "edit-item-carb"
                    ),
                }
            );

            closeModal(
                "modal-edit-item"
            );

            await onRefresh();
        }
    );
}