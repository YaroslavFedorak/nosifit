let timeoutId: number | undefined;

export function showRecoveryToast(
    message: string
): void {
    let toast =
        document.getElementById(
            "recovery-toast"
        );

    if (!toast) {
        toast =
            document.createElement("div");

        toast.id =
            "recovery-toast";

        toast.className =
            "recovery-toast";

        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("visible");

    if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
    }

    timeoutId =
        window.setTimeout(() => {
            toast?.classList.remove(
                "visible"
            );
        }, 2500);
}