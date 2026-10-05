import { NutritionAPI } from "../api.js";
import { normalizeMealCategory, suggestMealCategory } from "../categories.js";
import { describeError } from "../errors.js";
import { getLocale } from "../../i18n/index.js";
import type { Meal } from "../types.js";
import {
    closeModal,
    emitNutritionChange,
    getValue,
    onClick,
    openModal,
    setBusy,
    setModalError,
    setValue,
} from "./modal.js";

type RefreshCallback = () => void | Promise<void>;

const MODAL_ID = "modal-edit-meal";

export function openEditMealModal(meal: Meal): void {
    setValue("edit-meal-id", String(meal.id));
    setValue(
        "edit-meal-category",
        normalizeMealCategory(meal.category ?? meal.name) ?? suggestMealCategory(),
    );
    setValue("edit-meal-time", meal.time ?? "");
    openModal(MODAL_ID, "#edit-meal-category");
}

export function setupMealModals(onRefresh: RefreshCallback): void {
    onClick(["close-edit-meal"], () => closeModal(MODAL_ID));

    const save = document.getElementById("save-edit-meal") as HTMLButtonElement | null;

    save?.addEventListener("click", async () => {
        const id = Number(getValue("edit-meal-id"));
        const category = normalizeMealCategory(getValue("edit-meal-category"));

        if (!id || !category) return;

        setModalError(MODAL_ID, null);
        setBusy(save, true);

        try {
            await NutritionAPI.updateMeal(id, {
                category,
                time: getValue("edit-meal-time") || null,
                locale: getLocale(),
            });

            closeModal(MODAL_ID);
            emitNutritionChange("meals");
            await onRefresh();
        } catch (error) {
            setModalError(MODAL_ID, describeError(error));
        } finally {
            setBusy(save, false);
        }
    });
}
