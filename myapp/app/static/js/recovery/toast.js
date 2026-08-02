let timeoutId;

export function showRecoveryToast(message) {
    let toast = document.getElementById("recovery-toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "recovery-toast";
        toast.className = "recovery-toast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("visible");

    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => toast.classList.remove("visible"), 2500);
}
