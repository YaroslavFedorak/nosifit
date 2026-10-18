// Inline validation for auth forms marked with [data-validate].
// Messages come from data-msg-* attributes rendered by the template, so the
// errors follow the interface language instead of the browser's.
const messagesOf = (form) => ({
    required: form.dataset.msgRequired ?? "",
    email: form.dataset.msgEmail ?? "",
    range: form.dataset.msgRange ?? "",
    mismatch: form.dataset.msgMismatch ?? "",
    consent: form.dataset.msgConsent ?? "",
});
const holderOf = (control) => control.closest(".field, .check");
const messageFor = (control, messages) => {
    const validity = control.validity;
    if (validity.customError) {
        return control.validationMessage;
    }
    if (control instanceof HTMLInputElement && control.type === "checkbox") {
        return messages.consent;
    }
    if (validity.valueMissing) {
        return messages.required;
    }
    if (validity.typeMismatch && control.type === "email") {
        return messages.email;
    }
    if (validity.rangeUnderflow || validity.rangeOverflow) {
        const input = control;
        return messages.range.replace("{min}", input.min).replace("{max}", input.max);
    }
    return control.validationMessage;
};
const clear = (control) => {
    const holder = holderOf(control);
    holder?.classList.remove("is-invalid");
    holder?.querySelector(".field-error")?.remove();
    control.removeAttribute("aria-invalid");
};
const show = (control, text) => {
    const holder = holderOf(control);
    if (!holder) {
        return;
    }
    clear(control);
    holder.classList.add("is-invalid");
    control.setAttribute("aria-invalid", "true");
    const error = document.createElement("span");
    error.className = "field-error";
    error.id = `${control.name || control.id}-error`;
    error.textContent = text;
    holder.appendChild(error);
    control.setAttribute("aria-describedby", error.id);
};
const checkPasswordsMatch = (form, messages) => {
    const confirm = form.querySelector("[data-match]");
    if (!confirm) {
        return;
    }
    const original = form.querySelector(`#${confirm.dataset.match}`);
    const mismatch = Boolean(original && confirm.value && original.value !== confirm.value);
    confirm.setCustomValidity(mismatch ? messages.mismatch : "");
};
// Lets a multi-step form validate one step at a time.
export const validators = new WeakMap();
for (const form of document.querySelectorAll("form[data-validate]")) {
    const messages = messagesOf(form);
    const controls = () => Array.from(form.querySelectorAll("input, select")).filter((control) => control.willValidate);
    form.noValidate = true;
    // Checks the given controls (all of them by default) and shows what is wrong.
    const validate = (scope = controls()) => {
        checkPasswordsMatch(form, messages);
        const invalid = scope.filter((control) => !control.checkValidity());
        for (const control of scope) {
            clear(control);
        }
        for (const control of invalid) {
            show(control, messageFor(control, messages));
        }
        invalid[0]?.focus();
        return invalid.length === 0;
    };
    validators.set(form, validate);
    form.addEventListener("submit", (event) => {
        if (!validate()) {
            event.preventDefault();
            return;
        }
        form.querySelector("[type=submit]")?.setAttribute("aria-busy", "true");
    });
    // Re-check a field once the user corrects it.
    form.addEventListener("input", (event) => {
        const control = event.target;
        if (!holderOf(control)?.classList.contains("is-invalid")) {
            return;
        }
        checkPasswordsMatch(form, messages);
        if (control.checkValidity()) {
            clear(control);
        }
    });
    form.addEventListener("change", (event) => {
        const control = event.target;
        if (control.checkValidity()) {
            clear(control);
        }
    });
}
