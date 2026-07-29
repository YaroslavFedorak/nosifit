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
    const closeButtons = document.querySelectorAll("[data-close-calendar]");
    closeButtons.forEach(btn =>
        btn.addEventListener("click", () => {
            closeCalendarModal();
        })
    );
}
