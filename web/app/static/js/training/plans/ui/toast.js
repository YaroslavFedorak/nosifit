let timeoutId = null;
export function showToast(message) {
    let toast = document.getElementById("tr-plan-toast");
    if (!toast) {
        toast =
            document.createElement("div");
        toast.id =
            "tr-plan-toast";
        toast.className =
            "tr-plan-toast";
        document.body.appendChild(toast);
    }
    toast.textContent =
        message;
    toast.classList.add("visible");
    if (timeoutId) {
        clearTimeout(timeoutId);
    }
    timeoutId =
        setTimeout(() => {
            toast?.classList.remove("visible");
        }, 2000);
}
