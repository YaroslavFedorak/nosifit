let hideTimer:
    number | undefined;

export function showToast(
    message: string
): void {
    let toast =
        document.getElementById(
            "db-plan-toast"
        );

    if (!toast) {
        toast =
            document.createElement(
                "div"
            );

        toast.id =
            "db-plan-toast";

        toast.className =
            "db-plan-toast";

        document.body.appendChild(
            toast
        );
    }

    toast.textContent =
        message;

    toast.classList.add(
        "visible"
    );

    if (hideTimer !== undefined) {
        window.clearTimeout(
            hideTimer
        );
    }

    hideTimer =
        window.setTimeout(
            () => {
                toast?.classList.remove(
                    "visible"
                );
            },
            2000
        );
}