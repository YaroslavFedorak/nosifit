import { RecoveryAPI } from "../../api.js";
import { getLocale, recovery_t } from "../../../i18n/index.js";
import { createDailySummary, createHabitsGrid, createRecommendationRow } from "./components.js";
let initialized = false;
let requestSequence = 0;
let previousBodyOverflow = "";
function getUserId() {
    const app = document.getElementById("recovery-app");
    if (!app) {
        return null;
    }
    const userId = Number(app.dataset.userId);
    if (!Number.isFinite(userId) ||
        userId <= 0) {
        return null;
    }
    return userId;
}
function getElement(id) {
    return document.getElementById(id);
}
function formatDate(date) {
    const value = new Date(`${date}T12:00:00`);
    if (Number.isNaN(value.getTime())) {
        return date;
    }
    return new Intl.DateTimeFormat(getLocale(), {
        day: "numeric",
        month: "long",
        year: "numeric"
    }).format(value);
}
function renderLoading() {
    const title = getElement("rc-day-details-title");
    const subtitle = getElement("rc-day-details-subtitle");
    const summary = getElement("rc-day-details-summary");
    const habits = getElement("rc-day-habits");
    const recommendations = getElement("rc-day-recommendations");
    if (title) {
        title.textContent =
            recovery_t("day_details.loading");
    }
    if (subtitle) {
        subtitle.textContent =
            recovery_t("day_details.loading_subtitle");
    }
    if (summary) {
        summary.innerHTML =
            `
            <div class="rc-day-details-state">
                <div class="rc-day-details-spinner"></div>
                <div class="rc-day-details-state-text">
                    ${recovery_t("day_details.loading_data")}
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
function renderError(message) {
    const title = getElement("rc-day-details-title");
    const subtitle = getElement("rc-day-details-subtitle");
    const summary = getElement("rc-day-details-summary");
    const habits = getElement("rc-day-habits");
    const recommendations = getElement("rc-day-recommendations");
    const errorMessage = message ||
        recovery_t("day_details.load_error");
    if (title) {
        title.textContent =
            recovery_t("day_details.error");
    }
    if (subtitle) {
        subtitle.textContent =
            recovery_t("day_details.error_subtitle");
    }
    if (summary) {
        summary.innerHTML =
            `
            <div class="rc-day-details-state rc-day-details-state-error">
                <div class="rc-day-details-state-title">
                    ${recovery_t("day_details.load_error")}
                </div>
                <div class="rc-day-details-state-text">
                    ${errorMessage}
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
function renderDay(data) {
    const title = getElement("rc-day-details-title");
    const subtitle = getElement("rc-day-details-subtitle");
    const summary = getElement("rc-day-details-summary");
    const habitsSection = getElement("rc-day-habits");
    const recommendationsSection = getElement("rc-day-recommendations");
    const habitsCount = getElement("rc-habits-count");
    const habitsList = getElement("rc-habits-list");
    const recommendationsList = getElement("rc-recommendations-list");
    if (!title ||
        !subtitle ||
        !summary ||
        !habitsSection ||
        !recommendationsSection ||
        !habitsCount ||
        !habitsList ||
        !recommendationsList) {
        throw new Error(recovery_t("day_details.modal_missing"));
    }
    title.textContent =
        formatDate(data.date);
    subtitle.textContent =
        data.has_data
            ? recovery_t("day_details.full_subtitle")
            : recovery_t("day_details.partial_subtitle");
    summary.innerHTML = "";
    const summaryGrid = document.createElement("div");
    summaryGrid.id =
        "rc-day-summary-grid";
    summaryGrid.className =
        "rc-day-summary-grid";
    summaryGrid.appendChild(createDailySummary(data));
    summary.appendChild(summaryGrid);
    const dailySummary = document.createElement("div");
    dailySummary.id =
        "rc-day-daily-summary";
    dailySummary.className =
        "rc-day-daily-summary";
    const parts = [];
    if (data.training.sessions > 0) {
        parts.push(recovery_t("day_details.summary.training", {
            count: data.training.sessions
        }));
    }
    const sleepMinutes = data.sleep.duration_minutes;
    if (sleepMinutes !== null &&
        sleepMinutes !== undefined) {
        const hours = Math.floor(sleepMinutes / 60);
        const minutes = sleepMinutes % 60;
        parts.push(recovery_t("day_details.summary.sleep", {
            hours,
            minutes: String(minutes).padStart(2, "0")
        }));
    }
    if (data.habits.total > 0) {
        parts.push(recovery_t("day_details.summary.habits", {
            completed: data.habits.completed,
            total: data.habits.total
        }));
    }
    dailySummary.textContent =
        parts.length > 0
            ? parts.join(" · ")
            : recovery_t("day_details.no_extra_data");
    summary.appendChild(dailySummary);
    const habits = Array.isArray(data.habits.items)
        ? data.habits.items
        : [];
    habitsCount.textContent =
        data.habits.total > 0
            ? `${data.habits.completed}/${data.habits.total}`
            : "0";
    habitsList.innerHTML = "";
    const habitsGrid = createHabitsGrid(habits);
    habitsList.appendChild(habitsGrid);
    habitsList.classList.remove("expanded");
    const habitsToggle = getElement("rc-habits-toggle");
    if (habitsToggle) {
        habitsToggle.textContent =
            recovery_t("day_details.show_all");
        habitsToggle.classList.remove("is-expanded");
        habitsToggle.hidden =
            habits.length <= 4;
    }
    const recommendations = Array.isArray(data.recommendations.items)
        ? data.recommendations.items
        : [];
    recommendationsList.innerHTML = "";
    if (recommendations.length === 0) {
        const empty = document.createElement("div");
        empty.className =
            "rc-empty-state";
        empty.textContent =
            recovery_t("day_details.no_recommendations");
        recommendationsList.appendChild(empty);
    }
    else {
        recommendations.forEach((recommendation) => {
            recommendationsList.appendChild(createRecommendationRow(recommendation));
        });
    }
    habitsSection.hidden =
        false;
    recommendationsSection.hidden =
        false;
}
function showModal(modal) {
    previousBodyOverflow =
        document.body.style.overflow;
    document.body.style.overflow =
        "hidden";
    modal.setAttribute("aria-hidden", "false");
    modal.classList.add("open");
}
function hideModal(modal) {
    requestSequence += 1;
    modal.setAttribute("aria-hidden", "true");
    modal.classList.remove("open");
    document.body.style.overflow =
        previousBodyOverflow;
}
export function openDayDetails(date) {
    const modal = getElement("rc-day-details-modal");
    const userId = getUserId();
    if (!modal ||
        userId === null ||
        !date) {
        return;
    }
    const currentRequest = ++requestSequence;
    showModal(modal);
    renderLoading();
    RecoveryAPI
        .getDayDetails(userId, date)
        .then(data => {
        if (currentRequest !==
            requestSequence) {
            return;
        }
        if (data === null) {
            renderError(recovery_t("day_details.server_empty"));
            return;
        }
        try {
            renderDay(data);
        }
        catch (error) {
            console.error("[Recovery] Render error:", error);
            renderError(error instanceof Error
                ? error.message
                : recovery_t("day_details.render_error"));
        }
    })
        .catch(error => {
        if (currentRequest !==
            requestSequence) {
            return;
        }
        console.error("[Recovery] Day details error:", error);
        renderError(error instanceof Error
            ? error.message
            : recovery_t("day_details.load_error"));
    });
}
export function initDayDetailsModal() {
    if (initialized) {
        return;
    }
    const modal = getElement("rc-day-details-modal");
    if (!modal) {
        return;
    }
    initialized = true;
    const closeButton = modal.querySelector("[data-close-day-details]");
    closeButton?.addEventListener("click", () => {
        hideModal(modal);
    });
    const habitsToggle = getElement("rc-habits-toggle");
    habitsToggle?.addEventListener("click", () => {
        const habitsList = getElement("rc-habits-list");
        if (!habitsList) {
            return;
        }
        const expanded = habitsList.classList.toggle("expanded");
        habitsToggle.classList.toggle("is-expanded", expanded);
        habitsToggle.textContent =
            expanded
                ? recovery_t("day_details.show_less")
                : recovery_t("day_details.show_all");
    });
    modal.addEventListener("click", event => {
        if (event.target ===
            modal) {
            hideModal(modal);
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" &&
            modal.classList.contains("open")) {
            hideModal(modal);
        }
    });
}
