import { NutritionAPI } from "../api.js";
import { describeError } from "../errors.js";
import { nutrition_t } from "../../i18n/index.js";
import {
    closeModal,
    emitNutritionChange,
    getValue,
    markInvalid,
    onClick,
    openModal,
    parseNumber,
    setBusy,
    setModalError,
    setValue,
} from "./modal.js";

type RefreshCallback = () => void | Promise<void>;
type WaterMode = "add" | "remove";

const MODAL_ID = "modal-water";
const MAX_LITERS = 5;

let mode: WaterMode = "add";

function setMode(next: WaterMode): void {
    mode = next;

    document.querySelectorAll<HTMLButtonElement>(`#${MODAL_ID} [data-water-mode]`).forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.waterMode === mode));
    });

    const save = document.getElementById("save-water") as HTMLButtonElement | null;
    if (save) {
        save.textContent = mode === "add"
            ? (save.dataset.labelAdd ?? nutrition_t("actions.add"))
            : (save.dataset.labelRemove ?? nutrition_t("water.modeRemove"));
    }
}

/**
 * Water modal shared by the Nutrition page and the Dashboard.
 * `triggerIds` are the buttons that open it on the current page.
 */
export function setupWaterModal(
    onRefresh: RefreshCallback,
    triggerIds: string[] = ["add-water", "dashboard-add-water"],
): void {
    onClick(triggerIds, () => {
        setMode("add");
        setValue("water-amount", "");
        markInvalid("water-amount", false);
        openModal(MODAL_ID, "#water-amount");
    });

    onClick(["close-water-modal"], () => closeModal(MODAL_ID));

    document.querySelectorAll<HTMLButtonElement>(`#${MODAL_ID} [data-water-mode]`).forEach((button) => {
        button.addEventListener("click", () => setMode(button.dataset.waterMode as WaterMode));
    });

    document.querySelectorAll<HTMLButtonElement>(`#${MODAL_ID} [data-water-preset]`).forEach((button) => {
        button.addEventListener("click", () => {
            setValue("water-amount", button.dataset.waterPreset ?? "");
            markInvalid("water-amount", false);
            setModalError(MODAL_ID, null);
        });
    });

    const save = document.getElementById("save-water") as HTMLButtonElement | null;

    const submit = async (): Promise<void> => {
        const amount = parseNumber(getValue("water-amount"));

        if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_LITERS) {
            markInvalid("water-amount", true);
            setModalError(MODAL_ID, nutrition_t("errors.invalid_water"));
            return;
        }

        markInvalid("water-amount", false);
        setModalError(MODAL_ID, null);
        setBusy(save, true);

        try {
            await NutritionAPI.addWater(mode === "add" ? amount : -amount);
            closeModal(MODAL_ID);
            emitNutritionChange("water");
            await onRefresh();
        } catch (error) {
            setModalError(MODAL_ID, describeError(error));
        } finally {
            setBusy(save, false);
        }
    };

    save?.addEventListener("click", () => void submit());

    document.getElementById("water-amount")?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            void submit();
        }
    });
}
