let toastEl = null;
let timeoutId = null;

function getToastElement() {
    if (toastEl) {
        return toastEl;
    }

    toastEl = document.createElement("div");
    toastEl.id = "global-toast";
    toastEl.className = "global-toast";

    document.body.appendChild(toastEl);
    return toastEl;
}

export function showToast(message, type = "info") {
    const toast = getToastElement();

    toast.textContent = message;

    toast.classList.remove("info", "success", "error", "warning");
    toast.classList.add(type);

    toast.classList.add("visible");

    clearTimeout(timeoutId);

    timeoutId = setTimeout(() => {
        toast.classList.remove("visible");
    }, 2200);
}
