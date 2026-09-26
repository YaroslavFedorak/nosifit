import { profile_t } from "../i18n/index.js";

const OPEN_CLASS = "is-open";

const getModal = (
    id: string
): HTMLElement | null => {
    return document.getElementById(id);
};

const openModal = (
    modal: HTMLElement
): void => {
    modal.classList.add(OPEN_CLASS);
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("profile-modal-open");
};

const closeModal = (
    modal: HTMLElement
): void => {
    modal.classList.remove(OPEN_CLASS);
    modal.setAttribute("aria-hidden", "true");

    modal.dispatchEvent(
        new CustomEvent("modal:reset")
    );

    if (
        !document.querySelector(
            ".profile-modal-backdrop.is-open"
        )
    ) {
        document.body.classList.remove(
            "profile-modal-open"
        );
    }
};

const closeAllModals = (): void => {
    document
        .querySelectorAll<HTMLElement>(
            ".profile-modal-backdrop.is-open"
        )
        .forEach(closeModal);
};

const bindOpenButtons = (): void => {
    document
        .querySelectorAll<HTMLElement>(
            "[data-modal-open]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    const modalId =
                        button.dataset.modalOpen;

                    if (!modalId) {
                        return;
                    }

                    const modal =
                        getModal(modalId);

                    if (!modal) {
                        return;
                    }

                    openModal(modal);
                }
            );
        });
};

const bindCloseButtons = (): void => {
    document
        .querySelectorAll<HTMLElement>(
            "[data-modal-close]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    const modal =
                        button.closest<HTMLElement>(
                            ".profile-modal-backdrop"
                        );

                    if (!modal) {
                        return;
                    }

                    closeModal(modal);
                }
            );
        });
};

const bindBackdropClose = (): void => {
    document
        .querySelectorAll<HTMLElement>(
            ".profile-modal-backdrop"
        )
        .forEach((modal) => {
            modal.addEventListener(
                "click",
                (event) => {
                    if (
                        event.target !== modal
                    ) {
                        return;
                    }

                    closeModal(modal);
                }
            );
        });
};

const bindEscapeClose = (): void => {
    document.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "Escape") {
                return;
            }

            closeAllModals();
        }
    );
};

const bindPasswordToggles = (): void => {
    document
        .querySelectorAll<HTMLButtonElement>(
            "[data-password-toggle]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    const wrapper =
                        button.closest<HTMLElement>(
                            ".profile-password-wrapper"
                        );

                    if (!wrapper) {
                        return;
                    }

                    const input =
                        wrapper.querySelector<HTMLInputElement>(
                            ".profile-password-input"
                        );

                    if (!input) {
                        return;
                    }

                    const visible =
                        input.type === "text";

                    input.type =
                        visible
                            ? "password"
                            : "text";

                    button.textContent =
                        visible
                            ? profile_t(
                                "password.show"
                            )
                            : profile_t(
                                "password.hide"
                            );
                }
            );
        });
};

const bindPasswordForm = (): void => {
    const form =
        document.querySelector<HTMLFormElement>(
            "#modal-change-password form"
        );

    if (!form) {
        return;
    }

    form.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const submitButton =
                form.querySelector<HTMLButtonElement>(
                    'button[type="submit"]'
                );

            if (submitButton) {
                submitButton.disabled = true;
            }

            try {
                const response =
                    await fetch(
                        form.action,
                        {
                            method: "POST",
                            credentials:
                                "same-origin",
                            body:
                                new FormData(form)
                        }
                    );

                const data =
                    await response.json();

                if (!response.ok) {
                    if (
                        data.message ===
                        "wrong_old"
                    ) {
                        alert(
                            profile_t(
                                "password.errors.wrongOld"
                            )
                        );
                    } else if (
                        data.message ===
                        "mismatch"
                    ) {
                        alert(
                            profile_t(
                                "password.errors.mismatch"
                            )
                        );
                    } else if (
                        data.message ===
                        "same"
                    ) {
                        alert(
                            profile_t(
                                "password.errors.same"
                            )
                        );
                    } else {
                        alert(
                            profile_t(
                                "password.errors.changeFailed"
                            )
                        );
                    }

                    return;
                }

                if (
                    data.status ===
                    "success"
                ) {
                    alert(
                        profile_t(
                            "password.success"
                        )
                    );

                    const modal =
                        form.closest<HTMLElement>(
                            ".profile-modal-backdrop"
                        );

                    if (modal) {
                        closeModal(modal);
                    }
                }
            } catch {
                alert(
                    profile_t(
                        "password.errors.tryAgain"
                    )
                );
            } finally {
                if (submitButton) {
                    submitButton.disabled =
                        false;
                }
            }
        }
    );
};

export const initModals = (): void => {
    bindOpenButtons();
    bindCloseButtons();
    bindBackdropClose();
    bindEscapeClose();
    bindPasswordToggles();
    bindPasswordForm();
};