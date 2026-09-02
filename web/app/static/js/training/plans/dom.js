export const dom = {
    modal: document.getElementById("tr-plan-modal"),
    saveBtn: document.getElementById("tr-plan-save"),
    titleInput: document.getElementById("tr-plan-title"),
    summaryCount: document.getElementById("tr-plan-summary-count"),
    summarySets: document.getElementById("tr-plan-summary-sets"),
    daySummary: document.getElementById("tr-plan-day-summary"),
    emptyState: document.getElementById("tr-plan-empty"),
    container: document.getElementById("tr-plan-exercises"),
    addBtn: document.querySelector(".tr-plan-add-exercise"),
    emptyAddBtn: document.querySelector(".tr-plan-empty-add"),
    helpToggle: document.getElementById("tr-plan-help-toggle"),
    helpPopover: document.getElementById("tr-plan-help"),
    dayButtons: [],
    closeBtns: document.querySelectorAll("[data-close-plan]"),
    openBtn: document.getElementById("tr-edit-plan")
};
