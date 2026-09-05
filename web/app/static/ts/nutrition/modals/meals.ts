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
    const openButton =
        document.getElementById(
            "open-add-meal"
        );

    openButton?.addEventListener(
        "click",
        () => {
            setInputValue(
                "add-meal-name",
                ""
            );

            setInputValue(
                "add-meal-category",
                "Сніданок"
            );

            setInputValue(
                "add-meal-time",
                ""
            );

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
                getInputValue(
                    "add-meal-name"
                ).trim();

            if (!name) {
                return;
            }

            await NutritionAPI.createMeal({
                name,

                category:
                    getInputValue(
                        "add-meal-category"
                    ),

                time:
                    getInputValue(
                        "add-meal-time"
                    ) || null,
            });

            closeModal(
                "modal-add-meal"
            );

            await onRefresh();
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