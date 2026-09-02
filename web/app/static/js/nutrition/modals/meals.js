import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
    openModal,
} from "./modal.js";


export function setupMealModals(
    onRefresh,
) {
    const openButton =
        document.getElementById(
            "open-add-meal"
        );

    openButton?.addEventListener(
        "click",
        () => {
            document.getElementById(
                "add-meal-name"
            ).value = "";

            document.getElementById(
                "add-meal-category"
            ).value = "Сніданок";

            document.getElementById(
                "add-meal-time"
            ).value = "";

            openModal(
                "modal-add-meal"
            );
        }
    );

    document.getElementById(
        "close-add-meal"
    )?.addEventListener(
        "click",
        () => {
            closeModal(
                "modal-add-meal"
            );
        }
    );

    document.getElementById(
        "save-add-meal"
    )?.addEventListener(
        "click",
        async () => {
            const name =
                document.getElementById(
                    "add-meal-name"
                ).value.trim();

            if (!name) {
                return;
            }

            await NutritionAPI.createMeal({
                name,

                category:
                    document.getElementById(
                        "add-meal-category"
                    ).value,

                time:
                    document.getElementById(
                        "add-meal-time"
                    ).value || null,
            });

            closeModal(
                "modal-add-meal"
            );

            onRefresh();
        }
    );

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
                document.getElementById(
                    "edit-meal-id"
                ).value;

            const name =
                document.getElementById(
                    "edit-meal-name"
                ).value.trim();

            if (!id || !name) {
                return;
            }

            await NutritionAPI.updateMeal(
                id,
                {
                    name,

                    category:
                        document.getElementById(
                            "edit-meal-category"
                        ).value,

                    time:
                        document.getElementById(
                            "edit-meal-time"
                        ).value || null,
                }
            );

            closeModal(
                "modal-edit-meal"
            );

            onRefresh();
        }
    );
}