let hideTimer;

export function showToast(message) {
    let toast = document.getElementById("db-plan-toast");

    if (!toast) {
        toast = document.createElement("div");
        toast.id = "db-plan-toast";
        toast.className = "db-plan-toast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("visible");

    clearTimeout(hideTimer);
    hideTimer = window.setTimeout(() => {
        toast.classList.remove("visible");
    }, 2000);
}
