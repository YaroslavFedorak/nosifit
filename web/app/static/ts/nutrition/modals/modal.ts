export function openModal(id: string): void {
    const modal = document.getElementById(id);

    if (modal) {
        modal.classList.add("open");
    }
}

export function closeModal(id: string): void {
    const modal = document.getElementById(id);

    if (modal) {
        modal.classList.remove("open");
    }
}