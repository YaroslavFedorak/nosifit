import { RecoveryAPI } from "./api.js";
import { refreshRecoveryWidget } from "../../widgets/recovery/index.js";
import { RECOVERY_ICONS } from "../../../icons/recovery.js";

let initialized = false;

function getElement<T extends HTMLElement>(
    selector: string
): T | null {
    return document.querySelector<T>(selector);
}

function renderSleepIcon(): void {
    const icon =
        getElement<HTMLElement>(
            "#sleep-header-icon"
        );

    if (!icon) {
        return;
    }

    icon.innerHTML =
        RECOVERY_ICONS.moon;
}

function getLocalDateTime(
    date: string,
    time: string
): Date | null {
    const [year, month, day] =
        date.split("-").map(Number);

    const [hours, minutes] =
        time.split(":").map(Number);

    if (
        !Number.isInteger(year) ||
        !Number.isInteger(month) ||
        !Number.isInteger(day) ||
        !Number.isInteger(hours) ||
        !Number.isInteger(minutes)
    ) {
        return null;
    }

    const result = new Date(
        year,
        month - 1,
        day,
        hours,
        minutes,
        0,
        0
    );

    if (
        result.getFullYear() !== year ||
        result.getMonth() !== month - 1 ||
        result.getDate() !== day ||
        result.getHours() !== hours ||
        result.getMinutes() !== minutes
    ) {
        return null;
    }

    return result;
}

function resetForm(): void {
    const dateInput =
        getElement<HTMLInputElement>(
            "[data-sleep-date]"
        );

    const startInput =
        getElement<HTMLInputElement>(
            "[data-sleep-start-time]"
        );

    const endInput =
        getElement<HTMLInputElement>(
            "[data-sleep-end-time]"
        );

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

function closeModal(): void {
    const backdrop =
        getElement<HTMLElement>(
            "#sleep-modal-backdrop"
        );

    if (!backdrop) {
        return;
    }

    backdrop.classList.remove("open");

    window.setTimeout(() => {
        if (!backdrop.classList.contains("open")) {
            backdrop.hidden = true;
        }
    }, 180);

    resetForm();
}

function openModal(): void {
    const backdrop =
        getElement<HTMLElement>(
            "#sleep-modal-backdrop"
        );

    const dateInput =
        getElement<HTMLInputElement>(
            "[data-sleep-date]"
        );

    if (!backdrop) {
        return;
    }

    if (
        dateInput &&
        !dateInput.value
    ) {
        const now = new Date();

        const year =
            now.getFullYear();

        const month =
            String(
                now.getMonth() + 1
            ).padStart(2, "0");

        const day =
            String(
                now.getDate()
            ).padStart(2, "0");

        dateInput.value =
            `${year}-${month}-${day}`;
    }

    backdrop.hidden = false;

    requestAnimationFrame(() => {
        backdrop.classList.add("open");
    });
}

async function saveSleep(): Promise<void> {
    const dateInput =
        getElement<HTMLInputElement>(
            "[data-sleep-date]"
        );

    const startInput =
        getElement<HTMLInputElement>(
            "[data-sleep-start-time]"
        );

    const endInput =
        getElement<HTMLInputElement>(
            "[data-sleep-end-time]"
        );

    const saveButton =
        getElement<HTMLButtonElement>(
            "[data-save-sleep]"
        );

    if (
        !dateInput ||
        !startInput ||
        !endInput ||
        !saveButton
    ) {
        return;
    }

    const date =
        dateInput.value;

    const startTime =
        startInput.value;

    const endTime =
        endInput.value;

    if (
        !date ||
        !startTime ||
        !endTime
    ) {
        alert("Заповніть всі поля");
        return;
    }

    const startDate =
        getLocalDateTime(
            date,
            startTime
        );

    let endDate =
        getLocalDateTime(
            date,
            endTime
        );

    if (!startDate) {
        alert(
            "Некоректна дата або час початку сну"
        );
        return;
    }

    if (!endDate) {
        alert(
            "Некоректна дата або час завершення сну"
        );
        return;
    }

    if (endDate <= startDate) {
        endDate = new Date(
            endDate.getTime()
        );

        endDate.setDate(
            endDate.getDate() + 1
        );
    }

    if (endDate <= startDate) {
        alert(
            "Кінець сну має бути після початку"
        );
        return;
    }

    if (endDate > new Date()) {
        alert(
            "Сон не може закінчуватися у майбутньому"
        );
        return;
    }

    const recoveryButton =
        getElement<HTMLElement>(
            "#dashboard-open-recovery"
        );

    const userId =
        Number(
            recoveryButton?.getAttribute(
                "data-user-id"
            )
        );

    if (
        !Number.isFinite(userId) ||
        userId <= 0
    ) {
        alert(
            "Не вдалося визначити користувача"
        );
        return;
    }

    saveButton.disabled = true;

    try {
        await RecoveryAPI.addSleep(
            userId,
            startDate.toISOString(),
            endDate.toISOString()
        );

        await refreshRecoveryWidget();

        window.dispatchEvent(
            new CustomEvent(
                "dashboard:refresh"
            )
        );

        closeModal();
    } catch (error) {
        console.error(
            "Failed to save sleep:",
            error
        );

        alert(
            error instanceof Error
                ? error.message
                : "Не вдалося зберегти сон"
        );
    } finally {
        saveButton.disabled = false;
    }
}

function bindModal(
    backdrop: HTMLElement,
    openButton: HTMLButtonElement,
    closeButton: HTMLButtonElement,
    saveButton: HTMLButtonElement
): void {
    openButton.addEventListener(
        "click",
        openModal
    );

    closeButton.addEventListener(
        "click",
        closeModal
    );

    saveButton.addEventListener(
        "click",
        () => {
            void saveSleep();
        }
    );

    backdrop.addEventListener(
        "click",
        event => {
            if (event.target === backdrop) {
                closeModal();
            }
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape" &&
                backdrop.classList.contains("open")
            ) {
                closeModal();
            }
        }
    );
}

export function initSleepModal(): void {
    if (initialized) {
        return;
    }

    const initialize = (): void => {
        if (initialized) {
            return;
        }

        const backdrop =
            getElement<HTMLElement>(
                "#sleep-modal-backdrop"
            );

        const openButton =
            getElement<HTMLButtonElement>(
                "#dashboard-add-sleep"
            );

        const closeButton =
            getElement<HTMLButtonElement>(
                "[data-close-sleep]"
            );

        const saveButton =
            getElement<HTMLButtonElement>(
                "[data-save-sleep]"
            );

        if (
            !backdrop ||
            !openButton ||
            !closeButton ||
            !saveButton
        ) {
            return;
        }

        renderSleepIcon();

        initialized = true;

        bindModal(
            backdrop,
            openButton,
            closeButton,
            saveButton
        );
    };

    initialize();

    if (!initialized) {
        requestAnimationFrame(() => {
            initialize();
        });
    }
}
