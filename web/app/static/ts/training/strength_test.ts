import {
    TrainingAPI
} from "./api.js";

import {
    renderStrengthTestResults
} from "./dashboard.js";

import {
    t
} from "../i18n/index.js";

type StrengthType =
    | "pushups"
    | "squats"
    | "situps";

const TYPES: StrengthType[] = [
    "pushups",
    "squats",
    "situps"
];

function getInput(
    type: StrengthType
): HTMLInputElement | null {
    return document.getElementById(
        `st_${type}`
    ) as HTMLInputElement | null;
}

function getModal(): HTMLElement | null {
    return document.getElementById(
        "tr-modal-strength"
    );
}

function getSubmitButton(): HTMLButtonElement | null {
    return document.getElementById(
        "strength-test-submit"
    ) as HTMLButtonElement | null;
}

function getErrorElement(): HTMLElement | null {
    return document.getElementById(
        "strength-error"
    );
}

function getSuccessElement(): HTMLElement | null {
    return document.getElementById(
        "strength-success"
    );
}

function openModal(): void {
    const modal =
        getModal();

    if (!modal) {
        return;
    }

    modal.classList.add(
        "open"
    );
}

function closeModal(): void {
    const modal =
        getModal();

    if (!modal) {
        return;
    }

    modal.classList.remove(
        "open"
    );
}

function showError(
    message: string
): void {
    const error =
        getErrorElement();

    if (!error) {
        return;
    }

    error.textContent =
        message;

    error.classList.remove(
        "hidden"
    );
}

function hideError(): void {
    getErrorElement()?.classList.add(
        "hidden"
    );
}

function showSuccess(): void {
    getSuccessElement()?.classList.remove(
        "hidden"
    );
}

function hideSuccess(): void {
    getSuccessElement()?.classList.add(
        "hidden"
    );
}

function setLoading(
    loading: boolean
): void {
    const button =
        getSubmitButton();

    if (!button) {
        return;
    }

    button.disabled =
        loading;

    const text =
        button.querySelector<HTMLElement>(
            ".btn-text"
        );

    const loader =
        button.querySelector<HTMLElement>(
            ".btn-loader"
        );

    text?.classList.toggle(
        "hidden",
        loading
    );

    loader?.classList.toggle(
        "hidden",
        !loading
    );
}

function resetState(): void {
    hideError();
    hideSuccess();
}

export function injectIcons(): void {
    const icons: Record<
        StrengthType,
        string
    > = {
        pushups: "↗",
        squats: "↕",
        situps: "↔"
    };

    const fields =
        document.querySelectorAll<HTMLElement>(
            ".tr-strength-field"
        );

    fields.forEach(
        (field, index) => {
            const type =
                TYPES[index];

            if (!type) {
                return;
            }

            const icon =
                field.querySelector<HTMLElement>(
                    ".tr-strength-icon"
                );

            if (icon) {
                icon.textContent =
                    icons[type];
            }
        }
    );
}

export function setupArrows(): void {
    TYPES.forEach(
        type => {
            const input =
                getInput(type);

            if (!input) {
                return;
            }

            const increase =
                document.querySelector<HTMLElement>(
                    `[data-inc="st_${type}"]`
                );

            const decrease =
                document.querySelector<HTMLElement>(
                    `[data-dec="st_${type}"]`
                );

            increase?.addEventListener(
                "click",
                () => {
                    const value =
                        Math.max(
                            0,
                            Number(
                                input.value || 0
                            ) + 1
                        );

                    input.value =
                        String(value);

                    hideError();
                }
            );

            decrease?.addEventListener(
                "click",
                () => {
                    const value =
                        Math.max(
                            0,
                            Number(
                                input.value || 0
                            ) - 1
                        );

                    input.value =
                        String(value);

                    hideError();
                }
            );
        }
    );
}

async function submitTest(): Promise<void> {
    resetState();

    const pushups =
        Number(
            getInput(
                "pushups"
            )?.value || 0
        );

    const squats =
        Number(
            getInput(
                "squats"
            )?.value || 0
        );

    const situps =
        Number(
            getInput(
                "situps"
            )?.value || 0
        );

    if (
        !Number.isFinite(pushups) ||
        !Number.isFinite(squats) ||
        !Number.isFinite(situps)
    ) {
        showError(
            t("strengthTest.invalidValues")
        );

        return;
    }

    setLoading(
        true
    );

    try {
        const result =
            await TrainingAPI.strengthTest({
                pushups,
                squats,
                situps
            });

        const performance =
            result.raw_performance ??
            {
                pushups,
                squats,
                situps
            };

        renderStrengthTestResults(
            performance
        );

        showSuccess();
    } catch {
        showError(
            t("strengthTest.saveError")
        );
    } finally {
        setLoading(
            false
        );
    }
}

export function initStrengthTest(): void {
    const modal =
        getModal();

    if (!modal) {
        return;
    }

    const openButton =
        document.getElementById(
            "tr-strength-open"
        );

    const submitButton =
        getSubmitButton();

    injectIcons();
    setupArrows();

    openButton?.addEventListener(
        "click",
        () => {
            resetState();
            openModal();
        }
    );

    submitButton?.addEventListener(
        "click",
        async event => {
            event.preventDefault();

            await submitTest();
        }
    );

    modal
        .querySelectorAll<HTMLElement>(
            "[data-close-strength]"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    closeModal
                );
            }
        );

    modal.addEventListener(
        "click",
        event => {
            if (
                event.target === modal
            ) {
                closeModal();
            }
        }
    );
}