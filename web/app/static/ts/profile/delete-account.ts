const ACTIVE_CLASS = "active";

const getDeleteModal = (): HTMLElement | null => {
    return document.getElementById(
        "modal-delete-account"
    );
};

const getStep = (
    modal: HTMLElement,
    step: string
): HTMLElement | null => {
    return modal.querySelector<HTMLElement>(
        `[data-delete-step="${step}"]`
    );
};

const showStep = (
    modal: HTMLElement,
    step: string
): void => {
    modal
        .querySelectorAll<HTMLElement>(
            "[data-delete-step]"
        )
        .forEach((element) => {
            element.classList.toggle(
                ACTIVE_CLASS,
                element.dataset.deleteStep === step
            );
        });
};

const setButtonLoading = (
    button: HTMLButtonElement,
    loading: boolean,
    text: string
): void => {
    button.disabled = loading;
    button.textContent = text;
};

const bindSendCode = (
    modal: HTMLElement
): void => {
    const button =
        modal.querySelector<HTMLButtonElement>(
            "#delete-send-code"
        );

    if (!button) {
        return;
    }

    button.addEventListener(
        "click",
        async () => {
            setButtonLoading(
                button,
                true,
                "Надсилання..."
            );

            try {
                const response =
                    await fetch(
                        "/profile/delete/request",
                        {
                            method: "POST"
                        }
                    );

                const data =
                    await response.json();

                if (
                    data.status === "sent"
                ) {
                    showStep(modal, "2");
                    return;
                }

                button.textContent =
                    "Спробувати ще раз";
            } catch {
                button.textContent =
                    "Спробувати ще раз";
            } finally {
                button.disabled = false;
            }
        }
    );
};

const bindConfirmCode = (
    modal: HTMLElement
): void => {
    const button =
        modal.querySelector<HTMLButtonElement>(
            "#delete-confirm-btn"
        );

    const input =
        modal.querySelector<HTMLInputElement>(
            "#delete-confirm-code"
        );

    if (!button || !input) {
        return;
    }

    button.addEventListener(
        "click",
        async () => {
            const code =
                input.value.trim();

            if (!code) {
                input.focus();
                return;
            }

            setButtonLoading(
                button,
                true,
                "Перевірка..."
            );

            try {
                const response =
                    await fetch(
                        "/profile/delete/confirm",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                code
                            })
                        }
                    );

                const data =
                    await response.json();

                if (
                    data.status === "ok"
                ) {
                    showStep(modal, "3");
                    return;
                }

                button.textContent =
                    "Спробувати ще раз";
            } catch {
                button.textContent =
                    "Спробувати ще раз";
            } finally {
                button.disabled = false;
            }
        }
    );
};

const bindFinalDelete = (
    modal: HTMLElement
): void => {
    const button =
        modal.querySelector<HTMLButtonElement>(
            "#delete-final-btn"
        );

    const emailInput =
        modal.querySelector<HTMLInputElement>(
            "#delete-final-email"
        );

    const passwordInput =
        modal.querySelector<HTMLInputElement>(
            "#delete-final-password"
        );

    if (
        !button ||
        !emailInput ||
        !passwordInput
    ) {
        return;
    }

    button.addEventListener(
        "click",
        async () => {
            const email =
                emailInput.value.trim();

            const password =
                passwordInput.value;

            if (!email) {
                emailInput.focus();
                return;
            }

            if (!password) {
                passwordInput.focus();
                return;
            }

            setButtonLoading(
                button,
                true,
                "Видалення..."
            );

            try {
                const response =
                    await fetch(
                        "/profile/delete/final",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                email,
                                password
                            })
                        }
                    );

                const data =
                    await response.json();

                if (
                    data.status === "deleted"
                ) {
                    window.location.href =
                        "/login";

                    return;
                }

                button.textContent =
                    "Спробувати ще раз";
            } catch {
                button.textContent =
                    "Спробувати ще раз";
            } finally {
                button.disabled = false;
            }
        }
    );
};

const bindBackButtons = (
    modal: HTMLElement
): void => {
    modal
        .querySelectorAll<HTMLButtonElement>(
            "[data-delete-back]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    const step =
                        button.dataset.deleteBack;

                    if (
                        !step ||
                        !getStep(modal, step)
                    ) {
                        return;
                    }

                    showStep(
                        modal,
                        step
                    );
                }
            );
        });
};

const resetDeleteModal = (
    modal: HTMLElement
): void => {
    showStep(modal, "1");

    const codeInput =
        modal.querySelector<HTMLInputElement>(
            "#delete-confirm-code"
        );

    const passwordInput =
        modal.querySelector<HTMLInputElement>(
            "#delete-final-password"
        );

    const emailInput =
        modal.querySelector<HTMLInputElement>(
            "#delete-final-email"
        );

    if (codeInput) {
        codeInput.value = "";
    }

    if (passwordInput) {
        passwordInput.value = "";
    }

    if (emailInput) {
        emailInput.value = "";
    }

    const sendButton =
        modal.querySelector<HTMLButtonElement>(
            "#delete-send-code"
        );

    const confirmButton =
        modal.querySelector<HTMLButtonElement>(
            "#delete-confirm-btn"
        );

    const finalButton =
        modal.querySelector<HTMLButtonElement>(
            "#delete-final-btn"
        );

    if (sendButton) {
        sendButton.disabled = false;
        sendButton.textContent =
            "Надіслати код";
    }

    if (confirmButton) {
        confirmButton.disabled = false;
        confirmButton.textContent =
            "Підтвердити код";
    }

    if (finalButton) {
        finalButton.disabled = false;
        finalButton.textContent =
            "Видалити акаунт";
    }
};

export const initDeleteAccount = (): void => {
    const modal =
        getDeleteModal();

    if (!modal) {
        return;
    }

    bindSendCode(modal);
    bindConfirmCode(modal);
    bindFinalDelete(modal);
    bindBackButtons(modal);

    modal.addEventListener(
        "modal:reset",
        () => {
            resetDeleteModal(modal);
        }
    );
};