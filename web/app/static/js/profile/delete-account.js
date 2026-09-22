const ACTIVE_CLASS = "active";
const getDeleteModal = () => {
    return document.getElementById("modal-delete-account");
};
const getStep = (modal, step) => {
    return modal.querySelector(`[data-delete-step="${step}"]`);
};
const showStep = (modal, step) => {
    modal
        .querySelectorAll("[data-delete-step]")
        .forEach((element) => {
        element.classList.toggle(ACTIVE_CLASS, element.dataset.deleteStep === step);
    });
};
const setButtonLoading = (button, loading, text) => {
    button.disabled = loading;
    button.textContent = text;
};
const showError = (button, text) => {
    button.disabled = false;
    button.textContent = text;
};
const bindSendCode = (modal) => {
    const button = modal.querySelector("#delete-send-code");
    if (!button) {
        return;
    }
    button.addEventListener("click", async () => {
        setButtonLoading(button, true, "Надсилання...");
        try {
            const response = await fetch("/profile/delete/request", {
                method: "POST",
                credentials: "same-origin"
            });
            const data = await response.json();
            if (response.ok &&
                data.status === "sent") {
                showStep(modal, "2");
                return;
            }
            showError(button, "Спробувати ще раз");
        }
        catch {
            showError(button, "Спробувати ще раз");
        }
    });
};
const bindConfirmCode = (modal) => {
    const button = modal.querySelector("#delete-confirm-btn");
    const input = modal.querySelector("#delete-confirm-code");
    if (!button || !input) {
        return;
    }
    button.addEventListener("click", async () => {
        const code = input.value.trim();
        if (!code) {
            input.focus();
            return;
        }
        if (!/^\d{6}$/.test(code)) {
            input.focus();
            return;
        }
        setButtonLoading(button, true, "Перевірка...");
        try {
            const response = await fetch("/profile/delete/confirm", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    code
                })
            });
            const data = await response.json();
            if (response.ok &&
                data.status === "ok") {
                showStep(modal, "3");
                return;
            }
            if (data.status === "expired") {
                showError(button, "Код прострочений");
                return;
            }
            if (data.status === "wrong") {
                showError(button, "Неправильний код");
                return;
            }
            if (data.status ===
                "email_mismatch") {
                showError(button, "Email не збігається");
                return;
            }
            showError(button, "Спробувати ще раз");
        }
        catch {
            showError(button, "Спробувати ще раз");
        }
    });
};
const bindFinalDelete = (modal) => {
    const button = modal.querySelector("#delete-final-btn");
    const emailInput = modal.querySelector("#delete-final-email");
    const passwordInput = modal.querySelector("#delete-final-password");
    if (!button ||
        !emailInput ||
        !passwordInput) {
        return;
    }
    button.addEventListener("click", async () => {
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        if (!email) {
            emailInput.focus();
            return;
        }
        if (!password) {
            passwordInput.focus();
            return;
        }
        setButtonLoading(button, true, "Видалення...");
        try {
            const response = await fetch("/profile/delete/final", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email,
                    password
                })
            });
            const data = await response.json();
            if (response.ok &&
                data.status === "deleted") {
                window.location.href =
                    "/auth/login";
                return;
            }
            if (data.status ===
                "wrong_password") {
                showError(button, "Неправильний пароль");
                return;
            }
            if (data.status ===
                "email_mismatch") {
                showError(button, "Неправильний email");
                return;
            }
            if (data.status ===
                "expired") {
                showError(button, "Код прострочений");
                return;
            }
            showError(button, "Спробувати ще раз");
        }
        catch {
            showError(button, "Спробувати ще раз");
        }
    });
};
const bindBackButtons = (modal) => {
    modal
        .querySelectorAll("[data-delete-back]")
        .forEach((button) => {
        button.addEventListener("click", () => {
            const step = button.dataset.deleteBack;
            if (!step ||
                !getStep(modal, step)) {
                return;
            }
            showStep(modal, step);
        });
    });
};
const resetDeleteModal = (modal) => {
    showStep(modal, "1");
    const codeInput = modal.querySelector("#delete-confirm-code");
    const passwordInput = modal.querySelector("#delete-final-password");
    const emailInput = modal.querySelector("#delete-final-email");
    if (codeInput) {
        codeInput.value = "";
    }
    if (passwordInput) {
        passwordInput.value = "";
    }
    if (emailInput) {
        emailInput.value = "";
    }
    const sendButton = modal.querySelector("#delete-send-code");
    const confirmButton = modal.querySelector("#delete-confirm-btn");
    const finalButton = modal.querySelector("#delete-final-btn");
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
export const initDeleteAccount = () => {
    const modal = getDeleteModal();
    if (!modal) {
        return;
    }
    bindSendCode(modal);
    bindConfirmCode(modal);
    bindFinalDelete(modal);
    bindBackButtons(modal);
    modal.addEventListener("modal:reset", () => {
        resetDeleteModal(modal);
    });
};
