const getInput = (
    id: string
): HTMLInputElement | null =>
    document.getElementById(
        id
    ) as HTMLInputElement | null;

export const dom = {
    modal:
        document.getElementById(
            "tr-plan-modal"
        ),

    saveBtn:
        document.getElementById(
            "tr-plan-save"
        ) as HTMLButtonElement | null,

    titleInput:
        getInput("tr-plan-title"),

    summaryCount:
        document.getElementById(
            "tr-plan-summary-count"
        ),

    summarySets:
        document.getElementById(
            "tr-plan-summary-sets"
        ),

    daySummary:
        document.getElementById(
            "tr-plan-day-summary"
        ),

    emptyState:
        document.getElementById(
            "tr-plan-empty"
        ),

    container:
        document.getElementById(
            "tr-plan-exercises"
        ),

    addBtn:
        document.querySelector<HTMLElement>(
            ".tr-plan-add-exercise"
        ),

    emptyAddBtn:
        document.querySelector<HTMLElement>(
            ".tr-plan-empty-add"
        ),

    helpToggle:
        document.getElementById(
            "tr-plan-help-toggle"
        ),

    helpPopover:
        document.getElementById(
            "tr-plan-help"
        ),

    dayButtons: [] as HTMLButtonElement[],

    closeBtns:
        document.querySelectorAll<HTMLButtonElement>(
            "[data-close-plan]"
        ),

    openBtn:
        document.getElementById(
            "tr-edit-plan"
        ) as HTMLButtonElement | null
};