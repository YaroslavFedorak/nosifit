const getCompletionValue = (): number => {
    const element =
        document.querySelector<HTMLElement>(
            "[data-profile-completion]"
        );

    if (!element) {
        return 0;
    }

    const value = Number(
        element.dataset.profileCompletion
    );

    if (!Number.isFinite(value)) {
        return 0;
    }

    return Math.min(
        100,
        Math.max(0, value)
    );
};

const updateProgressCircle = (
    value: number
): void => {
    const circle =
        document.querySelector<HTMLElement>(
            "[data-progress-circle]"
        );

    if (!circle) {
        return;
    }

    circle.style.setProperty(
        "--progress",
        `${value}%`
    );

    circle.style.background =
        `conic-gradient(
            var(--profile-accent) 0 ${value}%,
            var(--profile-surface-soft) ${value}% 100%
        )`;
};

export const initProgress = (): void => {
    const value =
        getCompletionValue();

    updateProgressCircle(value);
};