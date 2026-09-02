let toastEl = null;
let timeoutId = null;

const VALID_TYPES = new Set(["info", "success", "warning", "error"]);
const TOAST_TYPES = ["info", "success", "warning", "error"];

function getToastElement() {
    if (toastEl) return toastEl;

    toastEl = document.createElement("div");
    toastEl.id = "global-toast";
    toastEl.className = "global-toast";
    document.body.appendChild(toastEl);

    return toastEl;
}

export function showToast(message, type = "info", duration = 2200) {
    const toast = getToastElement();
    const toastType = VALID_TYPES.has(type) ? type : "info";

    toast.textContent = message;

    toast.classList.remove(...TOAST_TYPES);
    toast.classList.add(toastType, "visible");

    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => toast.classList.remove("visible"), duration);
}
