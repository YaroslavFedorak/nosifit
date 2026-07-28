let toastEl = null;
let timeoutId = null;

export function showToast(message) {
    if (!toastEl) {
        toastEl = document.createElement("div");
        toastEl.id = "global-toast";
        toastEl.className = "global-toast";
        document.body.appendChild(toastEl);
    }

    toastEl.textContent = message;
    toastEl.classList.add("visible");

    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
        toastEl.classList.remove("visible");
    }, 2200);
}
