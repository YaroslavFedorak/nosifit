import {
    NutritionAPI,
} from "../api.js";

import {
    closeModal,
    openModal,
} from "./modal.js";

import type {
    MealItem,
} from "../types.js";


type RefreshCallback = () => void | Promise<void>;

export function openAddItemModal(mealId: number): void {
    const mealInput =
        document.getElementById("add-item-meal-id") as HTMLInputElement | null;

    if (!mealInput) {
        return;
    }

    mealInput.value = String(mealId);
    openModal("modal-add-item");
}


export function openEditItemModal(item: MealItem): void {
    const id =
        document.getElementById("edit-item-id") as HTMLInputElement | null;
    const name =
        document.getElementById("edit-item-name") as HTMLInputElement | null;
    const kcal =
        document.getElementById("edit-item-kcal") as HTMLInputElement | null;
    const protein =
        document.getElementById("edit-item-protein") as HTMLInputElement | null;
    const fat =
        document.getElementById("edit-item-fat") as HTMLInputElement | null;
    const carbs =
        document.getElementById("edit-item-carb") as HTMLInputElement | null;

    if (!id || !name || !kcal || !protein || !fat || !carbs) {
        return;
    }

    id.value = String(item.id);
    name.value = item.name;
    kcal.value = String(item.calories ?? 0);
    protein.value = String(item.protein ?? 0);
    fat.value = String(item.fat ?? 0);
    carbs.value = String(item.carbs ?? 0);

    openModal("modal-edit-item");
}




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