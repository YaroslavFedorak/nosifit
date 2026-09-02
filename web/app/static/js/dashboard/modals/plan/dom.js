export const dom = {
    modal: document.getElementById("db-plan-modal"),
    titleInput: document.getElementById("db-plan-title"),
    days: document.getElementById("db-plan-days"),
    exercises: document.getElementById("db-plan-exercises"),
    emptyState: document.getElementById("db-plan-empty"),
    addExerciseButton: document.querySelector(".db-plan-add-exercise"),
    emptyAddExerciseButton: document.querySelector(".db-plan-empty-add"),
    helpToggle: document.getElementById("db-plan-help-toggle"),
    helpPopover: document.getElementById("db-plan-help"),
    summaryCount: document.getElementById("db-plan-summary-count"),
    summarySets: document.getElementById("db-plan-summary-sets"),
    saveButton: document.getElementById("db-plan-save"),
    closeButtons: document.querySelectorAll("[data-close-plan-modal]")
};
