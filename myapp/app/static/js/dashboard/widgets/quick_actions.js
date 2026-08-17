export function initQuickActions() {
    const checkin = document.getElementById("open-checkin");
    const details = document.getElementById("open-day-details");
    if (checkin) checkin.addEventListener("click", () => {
        const ev = new CustomEvent("dashboard:open-checkin");
        window.dispatchEvent(ev);
    });
    if (details) details.addEventListener("click", () => {
        const ev = new CustomEvent("dashboard:open-day-details");
        window.dispatchEvent(ev);
    });
}
