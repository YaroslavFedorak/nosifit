/**
 * Shared behaviour for every nutrition modal (Nutrition page + Dashboard):
 * open/close, Escape, click on the backdrop, close buttons, focus handling,
 * inline errors and busy buttons.
 */

const openers = new Map<string, HTMLElement | null>();
let dismissInitialized = false;

function getModal(id: string): HTMLElement | null {
    return document.getElementById(id);
}

function topOpenModal(): HTMLElement | null {
    const open = Array.from(
        document.querySelectorAll<HTMLElement>(".modal.nf-modal.open"),
    );
    return open.length ? open[open.length - 1] : null;
}

function initDismiss(): void {
    if (dismissInitialized) return;
    dismissInitialized = true;

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const modal = topOpenModal();
        if (modal) {
            event.preventDefault();
            closeModal(modal.id);
        }
    });

    document.addEventListener("click", (event) => {
        const target = event.target as HTMLElement | null;
        if (!target) return;

        const closeButton = target.closest<HTMLElement>("[data-modal-close]");
        if (closeButton) {
            const modal = closeButton.closest<HTMLElement>(".modal.nf-modal");
            if (modal) closeModal(modal.id);
            return;
        }

        if (target.classList.contains("nf-modal") && target.classList.contains("open")) {
            closeModal(target.id);
        }
    });
}

export function openModal(id: string, focusSelector?: string): void {
    initDismiss();
    const modal = getModal(id);
    if (!modal) return;

    openers.set(id, document.activeElement as HTMLElement | null);
    setModalError(id, null);
    modal.classList.add("open");
    document.body.classList.add("nf-modal-open");

    // On touch screens auto-focus would pop the keyboard over the modal.
    if (!window.matchMedia("(pointer: fine)").matches) return;

    window.requestAnimationFrame(() => {
        const target = focusSelector
            ? modal.querySelector<HTMLElement>(focusSelector)
            : modal.querySelector<HTMLElement>("input:not([type=hidden]):not([readonly]), select, button:not([data-modal-close])");
        target?.focus({ preventScroll: true });
    });
}

export function closeModal(id: string): void {
    const modal = getModal(id);
    if (!modal || !modal.classList.contains("open")) return;

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

export function setModalError(id: string, message: string | null): void {
    const modal = getModal(id);
    const element = modal?.querySelector<HTMLElement>("[data-modal-error]");
    if (!element) return;

    element.textContent = message ?? "";
    element.hidden = !message;
}

export function setBusy(button: HTMLButtonElement | null, busy: boolean): void {
    if (!button) return;
    button.disabled = busy;
    button.setAttribute("aria-busy", String(busy));
}

export function getValue(id: string): string {
    const element = document.getElementById(id) as HTMLInputElement | HTMLSelectElement | null;
    return element?.value ?? "";
}

export function setValue(id: string, value: string): void {
    const element = document.getElementById(id) as HTMLInputElement | HTMLSelectElement | null;
    if (element) element.value = value;
}

/** Parses "1,5" as well as "1.5" (comma is the decimal separator in uk/pl/ru). */
export function parseNumber(value: string): number {
    const normalized = value.trim().replace(",", ".");
    if (!normalized) return Number.NaN;
    return Number(normalized);
}

export function markInvalid(id: string, invalid: boolean): void {
    const element = document.getElementById(id);
    if (!element) return;
    if (invalid) element.setAttribute("aria-invalid", "true");
    else element.removeAttribute("aria-invalid");
}

/** Notifies every widget on the page that nutrition data changed. */
export function emitNutritionChange(kind: "meals" | "water" | "weight"): void {
    window.dispatchEvent(new CustomEvent("nutrition:updated", { detail: { kind } }));

    if (kind === "water") {
        window.dispatchEvent(new CustomEvent("nutrition:water-updated"));
    }

    if (kind === "weight") {
        window.dispatchEvent(new CustomEvent("nutrition:weight-updated"));
    }
}

/** Binds a click handler to every element that exists among the given ids. */
export function onClick(ids: string[], handler: (event: MouseEvent) => void): void {
    ids.forEach((id) => {
        document.getElementById(id)?.addEventListener("click", handler);
    });
}
