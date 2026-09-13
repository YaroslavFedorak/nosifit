export function openDayModal(data) {
    const modal = document.getElementById("nf-day-modal");
    if (!modal) {
        return;
    }
    const date = modal.querySelector(".modal-date");
    const dailyScore = modal.querySelector(".modal-daily-score");
    const trainingScore = modal.querySelector(".modal-training-score");
    const nutritionScore = modal.querySelector(".modal-nutrition-score");
    const recoveryScore = modal.querySelector(".modal-recovery-score");
    if (date) {
        date.textContent =
            String(data.date);
    }
    if (dailyScore) {
        dailyScore.textContent =
            String(data.daily_score);
    }
    if (trainingScore) {
        trainingScore.textContent =
            String(data.training?.score ??
                0);
    }
    if (nutritionScore) {
        nutritionScore.textContent =
            String(data.nutrition?.score ??
                0);
    }
    if (recoveryScore) {
        recoveryScore.textContent =
            String(data.recovery?.score ??
                0);
    }
    modal.classList.add("open");
}
export function closeDayModal() {
    const modal = document.getElementById("nf-day-modal");
    if (!modal) {
        return;
    }
    modal.classList.remove("open");
}
