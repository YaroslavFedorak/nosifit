import { TrainingAPI } from "./api.js";
import { renderStrengthTestResults } from "./dashboard.js";
import { t } from "../i18n/index.js";
const TYPES = [
    "pushups",
    "squats",
    "situps"
];
function getInput(type) {
    return document.getElementById(`st_${type}`);
}
function getModal() {
    return document.getElementById("tr-modal-strength");
}
function getSubmitButton() {
    return document.getElementById("strength-test-submit");
}
function getErrorElement() {
    return document.getElementById("strength-error");
}
function getSuccessElement() {
    return document.getElementById("strength-success");
}
function openModal() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    modal.classList.add("open");
}
function closeModal() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    modal.classList.remove("open");
}
function showError(message) {
    const error = getErrorElement();
    if (!error) {
        return;
    }
    error.textContent =
        message;
    error.classList.remove("hidden");
}
function hideError() {
    getErrorElement()?.classList.add("hidden");
}
function showSuccess() {
    getSuccessElement()?.classList.remove("hidden");
}
function hideSuccess() {
    getSuccessElement()?.classList.add("hidden");
}
function setLoading(loading) {
    const button = getSubmitButton();
    if (!button) {
        return;
    }
    button.disabled =
        loading;
    const text = button.querySelector(".btn-text");
    const loader = button.querySelector(".btn-loader");
    text?.classList.toggle("hidden", loading);
    loader?.classList.toggle("hidden", !loading);
}
function resetState() {
    hideError();
    hideSuccess();
}
export function injectIcons() {
    const icons = {
        pushups: "↗",
        squats: "↕",
        situps: "↔"
    };
    const fields = document.querySelectorAll(".tr-strength-field");
    fields.forEach((field, index) => {
        const type = TYPES[index];
        if (!type) {
            return;
        }
        const icon = field.querySelector(".tr-strength-icon");
        if (icon) {
            icon.textContent =
                icons[type];
        }
    });
}
export function setupArrows() {
    TYPES.forEach(type => {
        const input = getInput(type);
        if (!input) {
            return;
        }
        const increase = document.querySelector(`[data-inc="st_${type}"]`);
        const decrease = document.querySelector(`[data-dec="st_${type}"]`);
        increase?.addEventListener("click", () => {
            const value = Math.max(0, Number(input.value || 0) + 1);
            input.value =
                String(value);
            hideError();
        });
        decrease?.addEventListener("click", () => {
            const value = Math.max(0, Number(input.value || 0) - 1);
            input.value =
                String(value);
            hideError();
        });
    });
}
async function submitTest() {
    resetState();
    const pushups = Number(getInput("pushups")?.value || 0);
    const squats = Number(getInput("squats")?.value || 0);
    const situps = Number(getInput("situps")?.value || 0);
    if (!Number.isFinite(pushups) ||
        !Number.isFinite(squats) ||
        !Number.isFinite(situps)) {
        showError(t("strengthTest.invalidValues"));
        return;
    }
    setLoading(true);
    try {
        const result = await TrainingAPI.strengthTest({
            pushups,
            squats,
            situps
        });
        const performance = result.raw_performance ??
            {
                pushups,
                squats,
                situps
            };
        renderStrengthTestResults(performance);
        showSuccess();
    }
    catch {
        showError(t("strengthTest.saveError"));
    }
    finally {
        setLoading(false);
    }
}
export function initStrengthTest() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    const openButton = document.getElementById("tr-strength-open");
    const submitButton = getSubmitButton();
    injectIcons();
    setupArrows();
    openButton?.addEventListener("click", () => {
        resetState();
        openModal();
    });
    submitButton?.addEventListener("click", async (event) => {
        event.preventDefault();
        await submitTest();
    });
    modal
        .querySelectorAll("[data-close-strength]")
        .forEach(button => {
        button.addEventListener("click", closeModal);
    });
    modal.addEventListener("click", event => {
        if (event.target === modal) {
            closeModal();
        }
    });
}
