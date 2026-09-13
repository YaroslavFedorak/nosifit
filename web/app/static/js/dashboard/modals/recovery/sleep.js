import { DashboardAPI } from "../../api.js";
let initialized = false;
function getElement(selector) {
    return document.querySelector(selector);
}
function getUserId() {
    const root = document.querySelector(".dashboard-page-wrapper");
    return root?.dataset.userId || null;
}
function getTomorrowDate(date) {
    const value = new Date(`${date}T00:00:00`);
    value.setDate(value.getDate() + 1);
    return value.toISOString().slice(0, 10);
}
function closeModal() {
    const backdrop = getElement("#sleep-modal-backdrop");
    const dateInput = getElement("[data-sleep-date]");
    const startInput = getElement("[data-sleep-start-time]");
    const endInput = getElement("[data-sleep-end-time]");
    backdrop?.classList.remove("open");
    if (dateInput) {
        dateInput.value = "";
    }
    if (startInput) {
        startInput.value = "";
    }
    if (endInput) {
        endInput.value = "";
    }
}
function openModal() {
    const backdrop = getElement("#sleep-modal-backdrop");
    const dateInput = getElement("[data-sleep-date]");
    if (!backdrop) {
        return;
    }
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date()
            .toISOString()
            .slice(0, 10);
    }
    backdrop.classList.add("open");
}
async function saveSleep() {
    const dateInput = getElement("[data-sleep-date]");
    const startInput = getElement("[data-sleep-start-time]");
    const endInput = getElement("[data-sleep-end-time]");
    const saveButton = getElement("[data-save-sleep]");
    if (!dateInput || !startInput || !endInput || !saveButton) {
        return;
    }
    const date = dateInput.value;
    const startTime = startInput.value;
    const endTime = endInput.value;
    if (!date || !startTime || !endTime) {
        alert("Заповніть всі поля");
        return;
    }
    const start = `${date}T${startTime}`;
    const endDate = endTime < startTime
        ? getTomorrowDate(date)
        : date;
    const end = `${endDate}T${endTime}`;
    const startDate = new Date(start);
    const endDateTime = new Date(end);
    if (Number.isNaN(startDate.getTime()) ||
        Number.isNaN(endDateTime.getTime())) {
        alert("Некоректні дані сну");
        return;
    }
    if (endDateTime <= startDate) {
        alert("Кінець сну має бути після початку");
        return;
    }
    if (endDateTime > new Date()) {
        alert("Сон не може закінчуватися у майбутньому");
        return;
    }
    const userId = getUserId();
    if (!userId) {
        alert("Не вдалося визначити користувача");
        return;
    }
    saveButton.disabled = true;
    try {
        await DashboardAPI.addSleep(userId, startDate.toISOString(), endDateTime.toISOString());
        closeModal();
        window.dispatchEvent(new CustomEvent("dashboard:recovery-updated"));
    }
    catch (error) {
        console.error("Failed to save sleep:", error);
        alert(error instanceof Error
            ? error.message
            : "Не вдалося зберегти сон");
    }
    finally {
        saveButton.disabled = false;
    }
}
export function initSleepModal() {
    if (initialized) {
        return;
    }
    const backdrop = getElement("#sleep-modal-backdrop");
    const openButton = getElement("#dashboard-add-sleep");
    const closeButton = getElement("[data-close-sleep]");
    const saveButton = getElement("[data-save-sleep]");
    if (!backdrop ||
        !openButton ||
        !closeButton ||
        !saveButton) {
        return;
    }
    initialized = true;
    openButton.addEventListener("click", openModal);
    closeButton.addEventListener("click", closeModal);
    saveButton.addEventListener("click", saveSleep);
    backdrop.addEventListener("click", (event) => {
        if (event.target === backdrop) {
            closeModal();
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" &&
            backdrop.classList.contains("open")) {
            closeModal();
        }
    });
}
