const OPEN_CLASS = "is-open";
const getModal = (id) => {
    return document.getElementById(id);
};
const openModal = (modal) => {
    modal.classList.add(OPEN_CLASS);
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("profile-modal-open");
};
const closeModal = (modal) => {
    modal.classList.remove(OPEN_CLASS);
    modal.setAttribute("aria-hidden", "true");
    modal.dispatchEvent(new CustomEvent("modal:reset"));
    if (!document.querySelector(".profile-modal-backdrop.is-open")) {
        document.body.classList.remove("profile-modal-open");
    }
};
const closeAllModals = () => {
    document
        .querySelectorAll(".profile-modal-backdrop.is-open")
        .forEach(closeModal);
};
const bindOpenButtons = () => {
    document
        .querySelectorAll("[data-modal-open]")
        .forEach((button) => {
        button.addEventListener("click", () => {
            const modalId = button.dataset.modalOpen;
            if (!modalId) {
                return;
            }
            const modal = getModal(modalId);
            if (!modal) {
                return;
            }
            openModal(modal);
        });
    });
};
const bindCloseButtons = () => {
    document
        .querySelectorAll("[data-modal-close]")
        .forEach((button) => {
        button.addEventListener("click", () => {
            const modal = button.closest(".profile-modal-backdrop");
            if (!modal) {
                return;
            }
            closeModal(modal);
        });
    });
};
const bindBackdropClose = () => {
    document
        .querySelectorAll(".profile-modal-backdrop")
        .forEach((modal) => {
        modal.addEventListener("click", (event) => {
            if (event.target !== modal) {
                return;
            }
            closeModal(modal);
        });
    });
};
const bindEscapeClose = () => {
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        closeAllModals();
    });
};
const bindPasswordToggles = () => {
    document
        .querySelectorAll("[data-password-toggle]")
        .forEach((button) => {
        button.addEventListener("click", () => {
            const wrapper = button.closest(".profile-password-wrapper");
            if (!wrapper) {
                return;
            }
            const input = wrapper.querySelector(".profile-password-input");
            if (!input) {
                return;
            }
            const visible = input.type === "text";
            input.type =
                visible
                    ? "password"
                    : "text";
            button.textContent =
                visible
                    ? "Показати"
                    : "Сховати";
        });
    });
};
const bindPasswordForm = () => {
    const form = document.querySelector("#modal-change-password form");
    if (!form) {
        return;
    }
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
        }
        try {
            const response = await fetch(form.action, {
                method: "POST",
                credentials: "same-origin",
                body: new FormData(form)
            });
            const data = await response.json();
            if (!response.ok) {
                if (data.message ===
                    "wrong_old") {
                    alert("Поточний пароль введено неправильно.");
                }
                else if (data.message ===
                    "mismatch") {
                    alert("Нові паролі не збігаються.");
                }
                else if (data.message ===
                    "same") {
                    alert("Новий пароль має відрізнятися від поточного.");
                }
                else {
                    alert("Не вдалося змінити пароль.");
                }
                return;
            }
            if (data.status ===
                "success") {
                alert("Пароль успішно змінено.");
                const modal = form.closest(".profile-modal-backdrop");
                if (modal) {
                    closeModal(modal);
                }
            }
        }
        catch {
            alert("Не вдалося змінити пароль. Спробуй ще раз.");
        }
        finally {
            if (submitButton) {
                submitButton.disabled =
                    false;
            }
        }
    });
};
export const initModals = () => {
    bindOpenButtons();
    bindCloseButtons();
    bindBackdropClose();
    bindEscapeClose();
    bindPasswordToggles();
    bindPasswordForm();
};
