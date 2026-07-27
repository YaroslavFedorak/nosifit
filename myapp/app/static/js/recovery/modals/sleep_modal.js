import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";

export function initSleepModal(userId) {
    const backdrop = document.getElementById("sleep-modal-backdrop");
    const openBtn = document.getElementById("open-sleep-modal");
    const closeBtn = document.querySelector("[data-close-sleep]");
    const saveBtn = document.querySelector("[data-save-sleep]");

    const dateInput = document.querySelector("[data-sleep-date]");
    const startTimeInput = document.querySelector("[data-sleep-start-time]");
    const endTimeInput = document.querySelector("[data-sleep-end-time]");

    if (!backdrop || !openBtn || !closeBtn || !saveBtn) return;

    const open = () => {
        backdrop.classList.add("open");
    };

    const close = () => {
        backdrop.classList.remove("open");
        dateInput.value = "";
        startTimeInput.value = "";
        endTimeInput.value = "";
    };

    const save = async () => {
        const date = dateInput.value;
        const startTime = startTimeInput.value;
        const endTime = endTimeInput.value;

        if (!date || !startTime || !endTime) {
            alert("Заповніть всі поля");
            return;
        }

        const start = `${date}T${startTime}`;
        let end = `${date}T${endTime}`;

        if (endTime < startTime) {
            const d = new Date(date);
            d.setDate(d.getDate() + 1);
            end = `${d.toISOString().slice(0, 10)}T${endTime}`;
        }

        const startDt = new Date(start);
        const endDt = new Date(end);
        const now = new Date();

        if (endDt > now) {
            alert("Сон не може закінчуватися у майбутньому");
            return;
        }

        saveBtn.disabled = true;

        try {
            const res = await RecoveryAPI.addSleep(
                userId,
                startDt.toISOString(),
                endDt.toISOString()
            );

            if (res?.error) {
                alert(res.error);
                return;
            }

            await RecoveryAPI.generateSnapshot(userId);
            await refreshRecoveryDashboard(userId);

            close();
        } finally {
            saveBtn.disabled = false;
        }
    };

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    saveBtn.addEventListener("click", save);
}
