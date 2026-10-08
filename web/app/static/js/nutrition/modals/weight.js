import { NutritionAPI } from "../api.js";
import { describeError } from "../errors.js";
import { nutrition_t } from "../../i18n/index.js";
import { closeModal, emitNutritionChange, getValue, markInvalid, onClick, openModal, parseNumber, setBusy, setModalError, setValue, } from "./modal.js";
const MODAL_ID = "modal-update-weight";
const MIN_WEIGHT = 20;
const MAX_WEIGHT = 400;
/**
 * Weight modal shared by the Nutrition page and the Dashboard.
 * Opens pre-filled with the current weight so a small change is one edit.
 */
export function setupWeightModal(onRefresh, triggerIds = ["open-update-weight", "dashboard-open-update-weight"]) {
    onClick(triggerIds, () => {
        setValue("update-weight-value", "");
        markInvalid("update-weight-value", false);
        openModal(MODAL_ID, "#update-weight-value");
        NutritionAPI.getWeight()
            .then((data) => {
            const input = document.getElementById("update-weight-value");
            if (input && !input.value && data.weight != null && Number.isFinite(data.weight)) {
                input.value = Number(data.weight).toFixed(1);
                input.select();
            }
        })
            .catch(() => undefined);
    });
    onClick(["close-update-weight"], () => closeModal(MODAL_ID));
    const save = document.getElementById("save-update-weight");
    const submit = async () => {
        const weight = parseNumber(getValue("update-weight-value"));
        if (!Number.isFinite(weight) || weight < MIN_WEIGHT || weight > MAX_WEIGHT) {
            markInvalid("update-weight-value", true);
            setModalError(MODAL_ID, nutrition_t("errors.invalid_weight"));
            return;
        }
        markInvalid("update-weight-value", false);
        setModalError(MODAL_ID, null);
        setBusy(save, true);
        try {
            await NutritionAPI.updateWeight(Math.round(weight * 10) / 10);
            closeModal(MODAL_ID);
            emitNutritionChange("weight");
            await onRefresh();
        }
        catch (error) {
            setModalError(MODAL_ID, describeError(error));
        }
        finally {
            setBusy(save, false);
        }
    };
    save?.addEventListener("click", () => void submit());
    document.getElementById("update-weight-value")?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            void submit();
        }
    });
}
