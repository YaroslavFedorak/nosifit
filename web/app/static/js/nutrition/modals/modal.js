/**
 * Shared behaviour for every nutrition modal (Nutrition page + Dashboard):
 * open/close, Escape, click on the backdrop, close buttons, focus handling,
 * inline errors and busy buttons.
 */
const openers = new Map();
let dismissInitialized = false;
function getModal(id) {
    return document.getElementById(id);
}
function topOpenModal() {
    const open = Array.from(document.querySelectorAll(".modal.nf-modal.open"));
    return open.length ? open[open.length - 1] : null;
}
function initDismiss() {
    if (dismissInitialized)
        return;
    dismissInitialized = true;
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape")
            return;
        const modal = topOpenModal();
        if (modal) {
            event.preventDefault();
            closeModal(modal.id);
        }
    });
    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!target)
            return;
        const closeButton = target.closest("[data-modal-close]");
        if (closeButton) {
            const modal = closeButton.closest(".modal.nf-modal");
            if (modal)
                closeModal(modal.id);
            return;
        }
        if (target.classList.contains("nf-modal") && target.classList.contains("open")) {
            closeModal(target.id);
        }
    });
}
export function openModal(id, focusSelector) {
    initDismiss();
    const modal = getModal(id);
    if (!modal)
        return;
    openers.set(id, document.activeElement);
    setModalError(id, null);
    modal.classList.add("open");
    document.body.classList.add("nf-modal-open");
    // On touch screens auto-focus would pop the keyboard over the modal.
    if (!window.matchMedia("(pointer: fine)").matches)
        return;
    window.requestAnimationFrame(() => {
        const target = focusSelector
            ? modal.querySelector(focusSelector)
            : modal.querySelector("input:not([type=hidden]):not([readonly]), select, button:not([data-modal-close])");
        target?.focus({ preventScroll: true });
    });
}
export function closeModal(id) {
    const modal = getModal(id);
    if (!modal || !modal.classList.contains("open"))
        return;
    modal.classList.remove("open");
    modal.dispatchEvent(new CustomEvent("nf-modal:closed"));
    if (!topOpenModal()) {
        document.body.classList.remove("nf-modal-open");
    }
    const opener = openers.get(id);
    openers.delete(id);
    if (opener && document.contains(opener)) {
        opener.focus({ preventScroll: true });
    }
}
export function setModalError(id, message) {
    const modal = getModal(id);
    const element = modal?.querySelector("[data-modal-error]");
    if (!element)
        return;
    element.textContent = message ?? "";
    element.hidden = !message;
}
export function setBusy(button, busy) {
    if (!button)
        return;
    button.disabled = busy;
    button.setAttribute("aria-busy", String(busy));
}
export function getValue(id) {
    const element = document.getElementById(id);
    return element?.value ?? "";
}
export function setValue(id, value) {
    const element = document.getElementById(id);
    if (element)
        element.value = value;
}
/** Parses "1,5" as well as "1.5" (comma is the decimal separator in uk/pl/ru). */
export function parseNumber(value) {
    const normalized = value.trim().replace(",", ".");
    if (!normalized)
        return Number.NaN;
    return Number(normalized);
}
export function markInvalid(id, invalid) {
    const element = document.getElementById(id);
    if (!element)
        return;
    if (invalid)
        element.setAttribute("aria-invalid", "true");
    else
        element.removeAttribute("aria-invalid");
}
/** Notifies every widget on the page that nutrition data changed. */
export function emitNutritionChange(kind) {
    window.dispatchEvent(new CustomEvent("nutrition:updated", { detail: { kind } }));
    if (kind === "water") {
        window.dispatchEvent(new CustomEvent("nutrition:water-updated"));
    }
    if (kind === "weight") {
        window.dispatchEvent(new CustomEvent("nutrition:weight-updated"));
    }
}
/** Binds a click handler to every element that exists among the given ids. */
export function onClick(ids, handler) {
    ids.forEach((id) => {
        document.getElementById(id)?.addEventListener("click", handler);
    });
}
