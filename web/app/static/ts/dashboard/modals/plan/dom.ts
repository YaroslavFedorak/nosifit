export interface PlanDOM {
    modal: HTMLElement | null;
    titleInput: HTMLInputElement | null;
    days: HTMLElement | null;
    exercises: HTMLElement | null;
    emptyState: HTMLElement | null;
    addExerciseButton: HTMLElement | null;
    emptyAddExerciseButton: HTMLElement | null;
    helpToggle: HTMLElement | null;
    helpPopover: HTMLElement | null;
    summaryCount: HTMLElement | null;
    summarySets: HTMLElement | null;
    saveButton: HTMLButtonElement | null;
    closeButtons: NodeListOf<HTMLElement>;
}

export const dom: PlanDOM = {
    modal:
        document.getElementById(
            "db-plan-modal"
        ),

    titleInput:
        document.getElementById(
            "db-plan-title"
        ) as HTMLInputElement | null,

    days:
        document.getElementById(
            "db-plan-days"
        ),

    exercises:
        document.getElementById(
            "db-plan-exercises"
        ),

    emptyState:
        document.getElementById(
            "db-plan-empty"
        ),

    addExerciseButton:
        document.querySelector(
            ".db-plan-add-exercise"
        ),

    emptyAddExerciseButton:
        document.querySelector(
            ".db-plan-empty-add"
        ),

    helpToggle:
        document.getElementById(
            "db-plan-help-toggle"
        ),

    helpPopover:
        document.getElementById(
            "db-plan-help"
        ),

    summaryCount:
        document.getElementById(
            "db-plan-summary-count"
        ),

    summarySets:
        document.getElementById(
            "db-plan-summary-sets"
        ),

    saveButton:
        document.getElementById(
            "db-plan-save"
        ) as HTMLButtonElement | null,

    closeButtons:
        document.querySelectorAll<HTMLElement>(
            "[data-close-plan-modal]"
        )
};