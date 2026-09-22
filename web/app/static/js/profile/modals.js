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
export const initModals = () => {
    bindOpenButtons();
    bindCloseButtons();
    bindBackdropClose();
    bindEscapeClose();
    bindPasswordToggles();
};
