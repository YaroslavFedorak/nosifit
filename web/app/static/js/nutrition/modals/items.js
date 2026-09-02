import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
} from "./modal.js";


function getNumber(id) {
    return Number(
        document.getElementById(id).value
        || 0
    );
}


export function setupItemModals(
    onRefresh,
) {
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
                document.getElementById(
                    "add-item-name"
                ).value.trim();

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

            onRefresh();
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
                document.getElementById(
                    "edit-item-id"
                ).value;

            const name =
                document.getElementById(
                    "edit-item-name"
                ).value.trim();

            if (!id || !name) {
                return;
            }

            await NutritionAPI.updateItem(
                id,
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

            onRefresh();
        }
    );
}