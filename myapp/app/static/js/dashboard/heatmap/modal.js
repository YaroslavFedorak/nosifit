export function openDayModal(data) {
    const modal = document.getElementById("nf-day-modal");
    if (!modal) return;
    modal.querySelector(".modal-date").textContent = data.date;
    modal.querySelector(".modal-daily-score").textContent = data.daily_score;
    modal.querySelector(".modal-training-score").textContent = data.training.score ?? 0;
    modal.querySelector(".modal-nutrition-score").textContent = data.nutrition.score ?? 0;
    modal.querySelector(".modal-recovery-score").textContent = data.recovery.score ?? 0;
    modal.classList.add("open");
}
export function closeDayModal() {
    const modal = document.getElementById("nf-day-modal");
    if (!modal) return;
    modal.classList.remove("open");
}
