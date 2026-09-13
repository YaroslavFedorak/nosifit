export function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add("open");
    }
}
export function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove("open");
    }
}
