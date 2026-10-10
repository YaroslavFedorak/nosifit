// Inline validation for auth forms marked with [data-validate].
// Messages come from data-msg-* attributes rendered by the template, so the
// errors follow the interface language instead of the browser's.

type Messages = {
    required: string;
    email: string;
    range: string;
    mismatch: string;
    consent: string;
};

const messagesOf = (form: HTMLFormElement): Messages => ({
    required: form.dataset.msgRequired ?? "",
    email: form.dataset.msgEmail ?? "",
    range: form.dataset.msgRange ?? "",
    mismatch: form.dataset.msgMismatch ?? "",
    consent: form.dataset.msgConsent ?? "",
});

type Control = HTMLInputElement | HTMLSelectElement;

const holderOf = (control: Control): HTMLElement | null =>
    control.closest<HTMLElement>(".field, .check");

const messageFor = (control: Control, messages: Messages): string => {
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
        const input = control as HTMLInputElement;
        return messages.range.replace("{min}", input.min).replace("{max}", input.max);
    }

    return control.validationMessage;
};

const clear = (control: Control): void => {
    const holder = holderOf(control);

    holder?.classList.remove("is-invalid");
    holder?.querySelector(".field-error")?.remove();
    control.removeAttribute("aria-invalid");
};

const show = (control: Control, text: string): void => {
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

const checkPasswordsMatch = (form: HTMLFormElement, messages: Messages): void => {
    const confirm = form.querySelector<HTMLInputElement>("[data-match]");

    if (!confirm) {
        return;
    }

    const original = form.querySelector<HTMLInputElement>(`#${confirm.dataset.match}`);
    const mismatch = Boolean(original && confirm.value && original.value !== confirm.value);

    confirm.setCustomValidity(mismatch ? messages.mismatch : "");
};

for (const form of document.querySelectorAll<HTMLFormElement>("form[data-validate]")) {
    const messages = messagesOf(form);
    const controls = (): Control[] =>
        Array.from(form.querySelectorAll<Control>("input, select")).filter(
            (control) => control.willValidate,
        );

    form.noValidate = true;

    form.addEventListener("submit", (event) => {
        checkPasswordsMatch(form, messages);

        const invalid = controls().filter((control) => !control.checkValidity());

        for (const control of controls()) {
            clear(control);
        }

        if (invalid.length === 0) {
            form.querySelector<HTMLButtonElement>("[type=submit]")?.setAttribute("aria-busy", "true");
            return;
        }

        event.preventDefault();

        for (const control of invalid) {
            show(control, messageFor(control, messages));
        }

        invalid[0].focus();
    });

    // Re-check a field once the user corrects it.
    form.addEventListener("input", (event) => {
        const control = event.target as Control;

        if (!holderOf(control)?.classList.contains("is-invalid")) {
            return;
        }

        checkPasswordsMatch(form, messages);

        if (control.checkValidity()) {
            clear(control);
        }
    });

    form.addEventListener("change", (event) => {
        const control = event.target as Control;

        if (control.checkValidity()) {
            clear(control);
        }
    });
}

export {};
