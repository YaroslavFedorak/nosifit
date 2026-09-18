function formatScore(value) {
    return value == null
        ? "—"
        : String(value);
}
function formatDate(dateString) {
    const date = new Date(`${dateString}T12:00:00`);
    return date.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}
function setModalState(modal, open) {
    modal.classList.toggle("open", open);
    modal.setAttribute("aria-hidden", String(!open));
}
function createMetric(label, value) {
    const metric = document.createElement("div");
    metric.className =
        "heatmap-day-details-metric";
    const metricLabel = document.createElement("span");
    metricLabel.className =
        "heatmap-day-details-metric-label";
    metricLabel.textContent =
        label;
    const metricValue = document.createElement("span");
    metricValue.className =
        "heatmap-day-details-metric-value";
    metricValue.textContent =
        formatScore(value);
    metric.append(metricLabel, metricValue);
    return metric;
}
function createSection(title, score) {
    const section = document.createElement("div");
    section.className =
        "heatmap-day-details-section";
    const header = document.createElement("div");
    header.className =
        "heatmap-day-details-section-header";
    const sectionTitle = document.createElement("span");
    sectionTitle.className =
        "heatmap-day-details-section-title";
    sectionTitle.textContent =
        title;
    const sectionScore = document.createElement("span");
    sectionScore.className =
        "heatmap-day-details-section-score";
    if (score == null) {
        sectionScore.classList.add("is-empty");
    }
    sectionScore.textContent =
        formatScore(score);
    header.append(sectionTitle, sectionScore);
    const metrics = document.createElement("div");
    metrics.className =
        "heatmap-day-details-metrics";
    metrics.appendChild(createMetric("Поточний показник", score));
    section.append(header, metrics);
    return section;
}
function renderDay(content, data) {
    content.innerHTML =
        "";
    if (!data.date) {
        const empty = document.createElement("div");
        empty.className =
            "heatmap-day-details-empty";
        empty.textContent =
            "Інформація про цей день недоступна.";
        content.appendChild(empty);
        return;
    }
    const wrapper = document.createElement("div");
    wrapper.className =
        "heatmap-day-details";
    const overview = document.createElement("div");
    overview.className =
        "heatmap-day-details-overview";
    const dateCard = document.createElement("div");
    dateCard.className =
        "heatmap-day-details-date";
    const dateLabel = document.createElement("span");
    dateLabel.className =
        "heatmap-day-details-date-label";
    dateLabel.textContent =
        "Дата";
    const dateValue = document.createElement("span");
    dateValue.className =
        "heatmap-day-details-date-value";
    dateValue.textContent =
        formatDate(data.date);
    dateCard.append(dateLabel, dateValue);
    const scoreCard = document.createElement("div");
    scoreCard.className =
        "heatmap-day-details-score";
    const scoreLabel = document.createElement("span");
    scoreLabel.className =
        "heatmap-day-details-score-label";
    scoreLabel.textContent =
        "Баланс дня";
    const scoreValue = document.createElement("span");
    scoreValue.className =
        "heatmap-day-details-score-value";
    if (data.daily_score == null) {
        scoreValue.classList.add("is-empty");
    }
    scoreValue.textContent =
        formatScore(data.daily_score);
    scoreCard.append(scoreLabel, scoreValue);
    overview.append(dateCard, scoreCard);
    const sections = document.createElement("div");
    sections.className =
        "heatmap-day-details-sections";
    sections.append(createSection("Тренування", data.training?.score), createSection("Відновлення", data.recovery?.score), createSection("Харчування", data.nutrition?.score));
    wrapper.append(overview, sections);
    content.appendChild(wrapper);
}
export function openDayModal(data) {
    const modal = document.getElementById("dashboard-day-details-modal");
    const content = document.getElementById("dashboard-day-details-content");
    const date = document.getElementById("dashboard-day-details-date");
    if (!modal ||
        !content) {
        return;
    }
    if (date) {
        date.textContent =
            data.date
                ? formatDate(data.date)
                : "—";
    }
    renderDay(content, data);
    setModalState(modal, true);
}
export function closeDayModal() {
    const modal = document.getElementById("dashboard-day-details-modal");
    if (!modal) {
        return;
    }
    setModalState(modal, false);
}
export function initDayDetailsModal() {
    const modal = document.getElementById("dashboard-day-details-modal");
    if (!modal) {
        return;
    }
    modal
        .querySelectorAll("[data-modal-close]")
        .forEach((element) => {
        element.addEventListener("click", closeDayModal);
    });
    document.addEventListener("dashboard:open-day", (event) => {
        const customEvent = event;
        if (!customEvent.detail) {
            return;
        }
        openDayModal(customEvent.detail);
    });
}
