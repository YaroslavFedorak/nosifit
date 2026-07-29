export function openCalendarModal() {
    const modal = document.getElementById("rc-calendar-modal");
    if (!modal) return;
    modal.classList.add("open");
}

export function closeCalendarModal() {
    const modal = document.getElementById("rc-calendar-modal");
    if (!modal) return;
    modal.classList.remove("open");
}

export function initCalendarModalControls() {
    const buttons = document.querySelectorAll("[data-close-calendar]");
    buttons.forEach(btn => btn.addEventListener("click", closeCalendarModal));
}
