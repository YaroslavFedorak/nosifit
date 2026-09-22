import { RecoveryAPI } from "../api.js";
import { refreshRecoveryDashboard } from "../dashboard.js";
import { ICONS } from "../../icons/index.js";

let initialized = false;

interface SleepModalElements {
    backdrop: HTMLElement;
    openBtn: HTMLElement;
    closeBtn: HTMLElement;
    saveBtn: HTMLButtonElement;
    dateInput: HTMLInputElement;
    startInput: HTMLInputElement;
    endInput: HTMLInputElement;
}

function getElements(): SleepModalElements | null {
    const backdrop =
        document.getElementById(
            "sleep-modal-backdrop"
        );

    const openBtn =
        document.getElementById(
            "open-sleep-modal"
        );

    const closeBtn =
        document.querySelector(
            "[data-close-sleep]"
        );

    const saveBtn =
        document.querySelector(
            "[data-save-sleep]"
        ) as HTMLButtonElement | null;

    const dateInput =
        document.querySelector(
            "[data-sleep-date]"
        ) as HTMLInputElement | null;

    const startInput =
        document.querySelector(
            "[data-sleep-start-time]"
        ) as HTMLInputElement | null;

    const endInput =
        document.querySelector(
            "[data-sleep-end-time]"
        ) as HTMLInputElement | null;

    if (
        !backdrop ||
        !openBtn ||
        !closeBtn ||
        !saveBtn ||
        !dateInput ||
        !startInput ||
        !endInput
    ) {
        return null;
    }

    return {
        backdrop,
        openBtn,
        closeBtn:
            closeBtn as HTMLElement,
        saveBtn,
        dateInput,
        startInput,
        endInput
    };
}

function getToday(): string {
    const today =
        new Date();

    return `${today.getFullYear()}-${String(
        today.getMonth() + 1
    ).padStart(2, "0")}-${String(
        today.getDate()
    ).padStart(2, "0")}`;
}

function openModal(
    elements: SleepModalElements
): void {
    elements.backdrop.hidden =
        false;

    requestAnimationFrame(() => {
        elements.backdrop.classList.add(
            "open"
        );
    });

    if (!elements.dateInput.value) {
        elements.dateInput.value =
            getToday();
    }

    document.body.classList.add(
        "modal-open"
    );
}

function closeModal(
    elements: SleepModalElements
): void {
    elements.backdrop.classList.remove(
        "open"
    );

    elements.backdrop.hidden =
        true;

    elements.dateInput.value = "";
    elements.startInput.value = "";
    elements.endInput.value = "";

    document.body.classList.remove(
        "modal-open"
    );
}

async function saveSleep(
    elements: SleepModalElements,
    userId: number
): Promise<void> {
    const date =
        elements.dateInput.value;

    const startTime =
        elements.startInput.value;

    const endTime =
        elements.endInput.value;

    if (
        !date ||
        !startTime ||
        !endTime
    ) {
        alert(
            "Заповніть усі поля"
        );

        return;
    }

    const start =
        new Date(
            `${date}T${startTime}`
        );

    const end =
        new Date(
            `${date}T${endTime}`
        );

    if (
        Number.isNaN(
            start.getTime()
        ) ||
        Number.isNaN(
            end.getTime()
        )
    ) {
        alert(
            "Некоректна дата або час"
        );

        return;
    }

    if (
        end.getTime() <=
        start.getTime()
    ) {
        end.setDate(
            end.getDate() + 1
        );
    }

    if (
        end.getTime() >
        Date.now()
    ) {
        alert(
            "Час завершення сну не може бути в майбутньому"
        );

        return;
    }

    elements.saveBtn.disabled =
        true;

    try {
        const response =
            await RecoveryAPI.addSleep(
                userId,
                start.toISOString(),
                end.toISOString()
            );

        if (
            response &&
            typeof response === "object" &&
            "error" in response &&
            typeof response.error === "string"
        ) {
            alert(
                response.error
            );

            return;
        }

        await refreshRecoveryDashboard(
            userId
        );

        closeModal(
            elements
        );
    } catch {
        alert(
            "Не вдалося зберегти сон"
        );
    } finally {
        elements.saveBtn.disabled =
            false;
    }
}

export function initSleepModal(
    userId: number
): void {
    if (initialized) {
        return;
    }

    const elements =
        getElements();

    if (!elements) {
        return;
    }

    initialized = true;

    const sleepIcon =
        document.getElementById(
            "sleep-header-icon"
        );

    if (sleepIcon) {
        sleepIcon.innerHTML =
            ICONS.moon;
    }

    elements.openBtn.addEventListener(
        "click",
        () => {
            openModal(elements);
        }
    );

    elements.closeBtn.addEventListener(
        "click",
        () => {
            closeModal(elements);
        }
    );

    elements.backdrop.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                elements.backdrop
            ) {
                closeModal(elements);
            }
        }
    );

    elements.saveBtn.addEventListener(
        "click",
        () => {
            void saveSleep(
                elements,
                userId
            );
        }
    );
}