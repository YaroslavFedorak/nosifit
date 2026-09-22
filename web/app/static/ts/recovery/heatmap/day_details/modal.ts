import {
    RecoveryAPI,
    type RecoveryDayDetails,
    type RecoveryHabit,
    type RecoveryRecommendation
} from "../../api.js";

import {
    createDailySummary,
    createHabitsGrid,
    createRecommendationRow
} from "./components.js";

let initialized = false;
let requestSequence = 0;
let previousBodyOverflow = "";

function getUserId(): number | null {
    const app =
        document.getElementById(
            "recovery-app"
        );

    if (!app) {
        return null;
    }

    const userId =
        Number(
            app.dataset.userId
        );

    if (
        !Number.isFinite(userId) ||
        userId <= 0
    ) {
        return null;
    }

    return userId;
}

function getElement<T extends HTMLElement>(
    id: string
): T | null {
    return document.getElementById(
        id
    ) as T | null;
}

function formatDate(
    date: string
): string {
    const value =
        new Date(
            `${date}T12:00:00`
        );

    if (
        Number.isNaN(
            value.getTime()
        )
    ) {
        return date;
    }

    return new Intl.DateTimeFormat(
        "uk-UA",
        {
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    ).format(value);
}

function renderLoading(): void {
    const title =
        getElement(
            "rc-day-details-title"
        );

    const subtitle =
        getElement(
            "rc-day-details-subtitle"
        );

    const summary =
        getElement(
            "rc-day-details-summary"
        );

    const habits =
        getElement(
            "rc-day-habits"
        );

    const recommendations =
        getElement(
            "rc-day-recommendations"
        );

    if (title) {
        title.textContent =
            "Завантаження";
    }

    if (subtitle) {
        subtitle.textContent =
            "Отримуємо дані за день";
    }

    if (summary) {
        summary.innerHTML =
            `
            <div class="rc-day-details-state">
                <div class="rc-day-details-spinner"></div>
                <div class="rc-day-details-state-text">
                    Завантаження даних…
                </div>
            </div>
            `;
    }

    if (habits) {
        habits.hidden = true;
    }

    if (recommendations) {
        recommendations.hidden = true;
    }
}

function renderError(
    message = "Не вдалося завантажити дані"
): void {
    const title =
        getElement(
            "rc-day-details-title"
        );

    const subtitle =
        getElement(
            "rc-day-details-subtitle"
        );

    const summary =
        getElement(
            "rc-day-details-summary"
        );

    const habits =
        getElement(
            "rc-day-habits"
        );

    const recommendations =
        getElement(
            "rc-day-recommendations"
        );

    if (title) {
        title.textContent =
            "Помилка";
    }

    if (subtitle) {
        subtitle.textContent =
            "Не вдалося відкрити дані за день";
    }

    if (summary) {
        summary.innerHTML =
            `
            <div class="rc-day-details-state rc-day-details-state-error">
                <div class="rc-day-details-state-title">
                    Не вдалося завантажити дані
                </div>
                <div class="rc-day-details-state-text">
                    ${message}
                </div>
            </div>
            `;
    }

    if (habits) {
        habits.hidden = true;
    }

    if (recommendations) {
        recommendations.hidden = true;
    }
}

function renderDay(
    data: RecoveryDayDetails
): void {
    const title =
        getElement(
            "rc-day-details-title"
        );

    const subtitle =
        getElement(
            "rc-day-details-subtitle"
        );

    const summary =
        getElement(
            "rc-day-details-summary"
        );

    const habitsSection =
        getElement(
            "rc-day-habits"
        );

    const recommendationsSection =
        getElement(
            "rc-day-recommendations"
        );

    const habitsCount =
        getElement(
            "rc-habits-count"
        );

    const habitsList =
        getElement(
            "rc-habits-list"
        );

    const recommendationsList =
        getElement(
            "rc-recommendations-list"
        );

    if (
        !title ||
        !subtitle ||
        !summary ||
        !habitsSection ||
        !recommendationsSection ||
        !habitsCount ||
        !habitsList ||
        !recommendationsList
    ) {
        throw new Error(
            "Не знайдено елемент модалки"
        );
    }

    title.textContent =
        formatDate(
            data.date
        );

    subtitle.textContent =
        data.has_data
            ? "Деталі відновлення за день"
            : "За цей день доступні лише часткові дані";

    summary.innerHTML = "";

    const summaryGrid =
        document.createElement(
            "div"
        );

    summaryGrid.id =
        "rc-day-summary-grid";

    summaryGrid.className =
        "rc-day-summary-grid";

    summaryGrid.appendChild(
        createDailySummary(
            data
        )
    );

    summary.appendChild(
        summaryGrid
    );

    const dailySummary =
        document.createElement(
            "div"
        );

    dailySummary.id =
        "rc-day-daily-summary";

    dailySummary.className =
        "rc-day-daily-summary";

    const parts: string[] = [];

    if (
        data.training.sessions > 0
    ) {
        parts.push(
            `Тренування: ${data.training.sessions}`
        );
    }

    const sleepMinutes =
        data.sleep.duration_minutes;

    if (
        sleepMinutes !== null &&
        sleepMinutes !== undefined
    ) {
        const hours =
            Math.floor(
                sleepMinutes / 60
            );

        const minutes =
            sleepMinutes % 60;

        parts.push(
            `Сон: ${hours} год ${String(minutes).padStart(2, "0")} хв`
        );
    }

    if (
        data.habits.total > 0
    ) {
        parts.push(
            `Звички: ${data.habits.completed}/${data.habits.total}`
        );
    }

    dailySummary.textContent =
        parts.length > 0
            ? parts.join(" · ")
            : "За цей день додаткових даних немає";

    summary.appendChild(
        dailySummary
    );

    const habits =
        Array.isArray(
            data.habits.items
        )
            ? data.habits.items
            : [];

    habitsCount.textContent =
        data.habits.total > 0
            ? `${data.habits.completed}/${data.habits.total}`
            : "0";

    habitsList.innerHTML = "";

    const habitsGrid =
        createHabitsGrid(
            habits
        );

    habitsList.appendChild(
        habitsGrid
    );

    habitsList.classList.remove(
        "expanded"
    );

    const habitsToggle =
        getElement<HTMLButtonElement>(
            "rc-habits-toggle"
        );

    if (habitsToggle) {
        habitsToggle.textContent =
            "Показати всі";

        habitsToggle.classList.remove(
            "is-expanded"
        );

        habitsToggle.hidden =
            habits.length <= 4;
    }

    const recommendations =
        Array.isArray(
            data.recommendations.items
        )
            ? data.recommendations.items
            : [];

    recommendationsList.innerHTML = "";

    if (
        recommendations.length === 0
    ) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "rc-empty-state";

        empty.textContent =
            "За цей день рекомендацій немає";

        recommendationsList.appendChild(
            empty
        );
    } else {
        recommendations.forEach(
            (
                recommendation: RecoveryRecommendation
            ) => {
                recommendationsList.appendChild(
                    createRecommendationRow(
                        recommendation
                    )
                );
            }
        );
    }

    habitsSection.hidden =
        false;

    recommendationsSection.hidden =
        false;
}

function showModal(
    modal: HTMLElement
): void {
    previousBodyOverflow =
        document.body.style.overflow;

    document.body.style.overflow =
        "hidden";

    modal.setAttribute(
        "aria-hidden",
        "false"
    );

    modal.classList.add(
        "open"
    );
}

function hideModal(
    modal: HTMLElement
): void {
    requestSequence += 1;

    modal.setAttribute(
        "aria-hidden",
        "true"
    );

    modal.classList.remove(
        "open"
    );

    document.body.style.overflow =
        previousBodyOverflow;
}

export function openDayDetails(
    date: string
): void {
    const modal =
        getElement<HTMLDivElement>(
            "rc-day-details-modal"
        );

    const userId =
        getUserId();

    if (
        !modal ||
        userId === null ||
        !date
    ) {
        return;
    }

    const currentRequest =
        ++requestSequence;

    showModal(
        modal
    );

    renderLoading();

    RecoveryAPI
        .getDayDetails(
            userId,
            date
        )
        .then(
            data => {
                if (
                    currentRequest !==
                    requestSequence
                ) {
                    return;
                }

                if (
                    data === null
                ) {
                    renderError(
                        "Сервер не повернув дані"
                    );
                    return;
                }

                try {
                    renderDay(
                        data
                    );
                } catch (
                    error
                ) {
                    console.error(
                        "[Recovery] Render error:",
                        error
                    );

                    renderError(
                        error instanceof Error
                            ? error.message
                            : "Помилка відображення даних"
                    );
                }
            }
        )
        .catch(
            error => {
                if (
                    currentRequest !==
                    requestSequence
                ) {
                    return;
                }

                console.error(
                    "[Recovery] Day details error:",
                    error
                );

                renderError(
                    error instanceof Error
                        ? error.message
                        : "Не вдалося завантажити дані"
                );
            }
        );
}

export function initDayDetailsModal(): void {
    if (
        initialized
    ) {
        return;
    }

    const modal =
        getElement<HTMLDivElement>(
            "rc-day-details-modal"
        );

    if (!modal) {
        return;
    }

    initialized = true;

    const closeButton =
        modal.querySelector<HTMLButtonElement>(
            "[data-close-day-details]"
        );

    closeButton?.addEventListener(
        "click",
        () => {
            hideModal(
                modal
            );
        }
    );

    const habitsToggle =
        getElement<HTMLButtonElement>(
            "rc-habits-toggle"
        );

    habitsToggle?.addEventListener(
        "click",
        () => {
            const habitsList =
                getElement<HTMLDivElement>(
                    "rc-habits-list"
                );

            if (
                !habitsList
            ) {
                return;
            }

            const expanded =
                habitsList.classList.toggle(
                    "expanded"
                );

            habitsToggle.classList.toggle(
                "is-expanded",
                expanded
            );

            habitsToggle.textContent =
                expanded
                    ? "Показати менше"
                    : "Показати всі";
        }
    );

    modal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                modal
            ) {
                hideModal(
                    modal
                );
            }
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape" &&
                modal.classList.contains(
                    "open"
                )
            ) {
                hideModal(
                    modal
                );
            }
        }
    );
}