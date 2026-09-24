import {
    TrainingAPI
} from "./api.js";

import type {
    DayDetailsResponse,
    HeatmapDay,
    HeatmapResponse
} from "./api.js";

import {
    exercise_t,
    getLocale,
    t
} from "../i18n/index.js";

let CALENDAR_DATA: HeatmapDay[] = [];

let CURRENT_YEAR =
    new Date().getFullYear();

let CURRENT_MONTH =
    new Date().getMonth();

let heatmapRequestId = 0;

const MONTH_KEYS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec"
];

function getMonthTranslation(
    month: number,
    full = false
): string {
    const key =
        MONTH_KEYS[month];

    if (!key) {
        return "";
    }

    return t(
        full
            ? `monthNames.${key}`
            : `months.${key}`
    );
}

function formatDate(
    date: Date
): string {
    return date.toLocaleDateString(
        getLocale(),
        {
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    );
}

function formatDateKey(
    date: Date
): string {
    const year =
        date.getFullYear();

    const month =
        String(
            date.getMonth() + 1
        ).padStart(
            2,
            "0"
        );

    const day =
        String(
            date.getDate()
        ).padStart(
            2,
            "0"
        );

    return `${year}-${month}-${day}`;
}

function getDayFromDate(
    date: string
): HeatmapDay | null {
    return (
        CALENDAR_DATA.find(
            day =>
                day.date === date
        ) ?? null
    );
}

function closeModal(
    id: string
): void {
    document
        .getElementById(id)
        ?.classList.remove(
            "open"
        );
}

export function initHeatmap(): void {
    const yearSelect =
        document.getElementById(
            "tr-heatmap-year"
        ) as HTMLSelectElement | null;

    const yearSelectCal =
        document.getElementById(
            "cal-year-select"
        ) as HTMLSelectElement | null;

    const openCalendar =
        document.getElementById(
            "tr-open-calendar"
        );

    const modal =
        document.getElementById(
            "tr-calendar-modal"
        );

    if (
        !yearSelect ||
        !yearSelectCal ||
        !openCalendar ||
        !modal
    ) {
        return;
    }

    CURRENT_YEAR =
        Number(
            yearSelect.value ||
            new Date().getFullYear()
        );

    CURRENT_MONTH =
        new Date().getMonth();

    yearSelectCal.value =
        String(
            CURRENT_YEAR
        );

    const load = (): void => {
        const year =
            Number(
                yearSelect.value
            );

        if (
            !Number.isFinite(year)
        ) {
            return;
        }

        CURRENT_YEAR =
            year;

        yearSelectCal.value =
            String(
                CURRENT_YEAR
            );

        const requestId =
            ++heatmapRequestId;

        TrainingAPI
            .getHeatmap(
                CURRENT_YEAR
            )
            .then(
                (
                    data: HeatmapResponse
                ) => {
                    if (
                        requestId !==
                        heatmapRequestId
                    ) {
                        return;
                    }

                    CALENDAR_DATA =
                        Array.isArray(
                            data?.days
                        )
                            ? data.days
                            : [];

                    renderHeatmap(
                        CALENDAR_DATA
                    );

                    renderCalendarMonth();
                }
            )
            .catch(() => {
                if (
                    requestId !==
                    heatmapRequestId
                ) {
                    return;
                }

                CALENDAR_DATA = [];

                renderHeatmap([]);

                renderCalendarMonth();
            });
    };

    setupHeatmapEvents();

    load();

    yearSelect.addEventListener(
        "change",
        load
    );

    yearSelectCal.addEventListener(
        "change",
        () => {
            const year =
                Number(
                    yearSelectCal.value
                );

            if (
                !Number.isFinite(year)
            ) {
                return;
            }

            CURRENT_YEAR =
                year;

            CURRENT_MONTH = 0;

            yearSelect.value =
                String(
                    CURRENT_YEAR
                );

            load();
        }
    );

    openCalendar.addEventListener(
        "click",
        () => {
            renderCalendarMonth();

            modal.classList.add(
                "open"
            );
        }
    );

    document
        .querySelectorAll<HTMLElement>(
            "[data-close-calendar]"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        closeModal(
                            "tr-calendar-modal"
                        );
                    }
                );
            }
        );

    document
        .querySelectorAll<HTMLElement>(
            "[data-close-day-details]"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        closeModal(
                            "tr-day-details-modal"
                        );
                    }
                );
            }
        );

    const prevButton =
        document.getElementById(
            "cal-prev"
        );

    const nextButton =
        document.getElementById(
            "cal-next"
        );

    prevButton?.addEventListener(
        "click",
        () => {
            CURRENT_MONTH -= 1;

            if (
                CURRENT_MONTH < 0
            ) {
                CURRENT_MONTH = 11;
                CURRENT_YEAR -= 1;

                yearSelect.value =
                    String(
                        CURRENT_YEAR
                    );

                yearSelectCal.value =
                    String(
                        CURRENT_YEAR
                    );

                load();

                return;
            }

            renderCalendarMonth();
        }
    );

    nextButton?.addEventListener(
        "click",
        () => {
            CURRENT_MONTH += 1;

            if (
                CURRENT_MONTH > 11
            ) {
                CURRENT_MONTH = 0;
                CURRENT_YEAR += 1;

                yearSelect.value =
                    String(
                        CURRENT_YEAR
                    );

                yearSelectCal.value =
                    String(
                        CURRENT_YEAR
                    );

                load();

                return;
            }

            renderCalendarMonth();
        }
    );

    modal.addEventListener(
        "click",
        event => {
            if (
                event.target === modal
            ) {
                closeModal(
                    "tr-calendar-modal"
                );
            }
        }
    );

    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key !== "Escape"
            ) {
                return;
            }

            closeModal(
                "tr-calendar-modal"
            );

            closeModal(
                "tr-day-details-modal"
            );
        }
    );
}

function setupHeatmapEvents(): void {
    const grid =
        document.getElementById(
            "training-heatmap"
        );

    if (!grid) {
        return;
    }

    grid.addEventListener(
        "click",
        event => {
            const target =
                event.target as HTMLElement;

            const cell =
                target.closest(
                    ".heatmap-cell"
                ) as HTMLElement | null;

            if (!cell) {
                return;
            }

            const date =
                cell.dataset.date;

            if (!date) {
                return;
            }

            openDayDetails(
                date
            );
        }
    );

    grid.addEventListener(
        "pointerover",
        event => {
            const target =
                event.target as HTMLElement;

            const cell =
                target.closest(
                    ".heatmap-cell"
                ) as HTMLElement | null;

            if (!cell) {
                return;
            }

            const relatedTarget =
                event.relatedTarget as Node | null;

            if (
                relatedTarget &&
                cell.contains(
                    relatedTarget
                )
            ) {
                return;
            }

            showHeatmapTooltip(
                cell
            );
        }
    );

    grid.addEventListener(
        "pointerout",
        event => {
            const target =
                event.target as HTMLElement;

            const cell =
                target.closest(
                    ".heatmap-cell"
                ) as HTMLElement | null;

            if (!cell) {
                return;
            }

            const relatedTarget =
                event.relatedTarget as Node | null;

            if (
                relatedTarget &&
                cell.contains(
                    relatedTarget
                )
            ) {
                return;
            }

            hideHeatmapTooltip();
        }
    );

    grid.addEventListener(
        "pointerleave",
        hideHeatmapTooltip
    );
}

function getHeatmapTooltip(): HTMLDivElement {
    let tooltip =
        document.getElementById(
            "heatmap-tooltip"
        ) as HTMLDivElement | null;

    if (tooltip) {
        return tooltip;
    }

    tooltip =
        document.createElement(
            "div"
        );

    tooltip.id =
        "heatmap-tooltip";

    tooltip.className =
        "heatmap-tooltip";

    document.body.appendChild(
        tooltip
    );

    return tooltip;
}

function showHeatmapTooltip(
    cell: HTMLElement
): void {
    const tooltip =
        getHeatmapTooltip();

    const percent =
        Number(
            cell.dataset.percent
        ) || 0;

    const load =
        Number(
            cell.dataset.load
        ) || 0;

    tooltip.textContent =
        t(
            "heatmap.load",
            {
                percent,
                load
            }
        );

    tooltip.classList.add(
        "is-visible"
    );

    const rect =
        cell.getBoundingClientRect();

    const tooltipRect =
        tooltip.getBoundingClientRect();

    const gap = 8;

    let top =
        rect.top -
        tooltipRect.height -
        gap;

    if (
        top < 8
    ) {
        top =
            rect.bottom +
            gap;
    }

    let left =
        rect.left +
        rect.width / 2 -
        tooltipRect.width / 2;

    const maxLeft =
        window.innerWidth -
        tooltipRect.width -
        8;

    left =
        Math.max(
            8,
            Math.min(
                left,
                maxLeft
            )
        );

    tooltip.style.left =
        `${left}px`;

    tooltip.style.top =
        `${top}px`;
}

function hideHeatmapTooltip(): void {
    const tooltip =
        document.getElementById(
            "heatmap-tooltip"
        ) as HTMLDivElement | null;

    if (!tooltip) {
        return;
    }

    tooltip.classList.remove(
        "is-visible"
    );
}

function renderMonths(): void {
    const months =
        document.getElementById(
            "training-heatmap-months"
        );

    if (!months) {
        return;
    }

    months.innerHTML =
        MONTH_KEYS
            .map(
                (_, index) =>
                    `<span>${getMonthTranslation(index)}</span>`
            )
            .join("");
}

function createEmptyDay(
    date: string
): HeatmapDay {
    return {
        date,
        level: 0,
        percent: 0,
        load: 0,
        is_today: false
    };
}

function renderHeatmap(
    days: HeatmapDay[]
): void {
    const grid =
        document.getElementById(
            "training-heatmap"
        );

    if (!grid) {
        return;
    }

    const data =
        new Map<
            string,
            HeatmapDay
        >();

    for (
        const day of days
    ) {
        if (
            typeof day.date ===
            "string"
        ) {
            data.set(
                day.date,
                day
            );
        }
    }

    const start =
        new Date(
            CURRENT_YEAR,
            0,
            1
        );

    const end =
        new Date(
            CURRENT_YEAR,
            11,
            31
        );

    const cells: string[] = [];

    const current =
        new Date(start);

    while (
        current <= end
    ) {
        const dateString =
            formatDateKey(
                current
            );

        const day =
            data.get(
                dateString
            ) ??
            createEmptyDay(
                dateString
            );

        let level =
            Number(
                day.level
            );

        if (
            !Number.isFinite(level)
        ) {
            level = 0;
        }

        level =
            Math.max(
                0,
                Math.min(
                    6,
                    Math.round(level)
                )
            );

        const percent =
            Number(
                day.percent
            ) || 0;

        const load =
            Number(
                day.load
            ) || 0;

        const todayClass =
            day.is_today
                ? " today"
                : "";

        cells.push(
            `
                <div
                    class="heatmap-cell${todayClass}"
                    data-date="${dateString}"
                    data-level="${level}"
                    data-percent="${percent}"
                    data-load="${load}"
                    role="gridcell"
                    aria-label="${t(
                        "heatmap.ariaLabel",
                        {
                            date: formatDate(
                                current
                            ),
                            percent
                        }
                    )}"
                ></div>
            `
        );

        current.setDate(
            current.getDate() + 1
        );
    }

    renderMonths();

    grid.innerHTML =
        cells.join("");
}

function renderCalendarMonth(): void {
    const grid =
        document.getElementById(
            "tr-calendar-grid"
        );

    const title =
        document.getElementById(
            "cal-month-title"
        );

    if (
        !grid ||
        !title
    ) {
        return;
    }

    title.textContent =
        `${getMonthTranslation(
            CURRENT_MONTH,
            true
        )} ${CURRENT_YEAR}`;

    const days =
        CALENDAR_DATA.filter(
            day => {
                if (!day.date) {
                    return false;
                }

                const date =
                    new Date(
                        `${day.date}T12:00:00`
                    );

                return (
                    date.getFullYear() ===
                        CURRENT_YEAR &&
                    date.getMonth() ===
                        CURRENT_MONTH
                );
            }
        );

    grid.innerHTML =
        days
            .map(
                day => {
                    const date =
                        new Date(
                            `${day.date}T12:00:00`
                        );

                    const level =
                        Math.max(
                            0,
                            Math.min(
                                6,
                                Math.round(
                                    Number(
                                        day.level
                                    ) || 0
                                )
                            )
                        );

                    const percent =
                        Number(
                            day.percent
                        ) || 0;

                    return `
                        <div
                            class="tr-calendar-item tr-level-${level}"
                            data-date="${day.date}"
                        >
                            <div class="tr-calendar-date">
                                ${date.getDate()}
                            </div>
                            <div class="tr-calendar-load">
                                ${percent}%
                            </div>
                        </div>
                    `;
                }
            )
            .join("");

    grid.onclick =
        event => {
            const target =
                event.target as HTMLElement;

            const item =
                target.closest(
                    ".tr-calendar-item"
                ) as HTMLElement | null;

            if (!item) {
                return;
            }

            const date =
                item.dataset.date;

            if (date) {
                openDayDetails(
                    date
                );
            }
        };
}

function getDayExerciseName(
    exercise: {
        name?: string;
        slug?: string;
    }
): string {
    if (
        typeof exercise.slug === "string" &&
        exercise.slug.trim()
    ) {
        const translated =
            exercise_t(exercise.slug);

        if (
            translated !==
            `${exercise.slug}.name`
        ) {
            return translated;
        }
    }

    return exercise.name ||
        t("exercise.fallback");
}

function openDayDetails(
    date: string
): void {
    TrainingAPI
        .getDayDetails(
            date
        )
        .then(
            (
                data: DayDetailsResponse
            ) => {
                const modal =
                    document.getElementById(
                        "tr-day-details-modal"
                    );

                const title =
                    document.getElementById(
                        "tr-day-details-title"
                    );

                const body =
                    document.getElementById(
                        "tr-day-details-body"
                    );

                if (
                    !modal ||
                    !title ||
                    !body
                ) {
                    return;
                }

                const parsedDate =
                    new Date(
                        `${date}T12:00:00`
                    );

                title.textContent =
                    formatDate(
                        parsedDate
                    );

                const sessions =
                    Array.isArray(
                        data?.sessions
                    )
                        ? data.sessions
                        : [];

                if (
                    !sessions.length
                ) {
                    body.innerHTML =
                        `<p>${t(
                            "heatmap.emptyDay"
                        )}</p>`;
                } else {
                    body.innerHTML =
                        sessions
                            .map(
                                session => `
                                    <div class="tr-day-session">
                                        <div class="tr-day-session-title">
                                            ${t(
                                                "heatmap.session"
                                            )}
                                        </div>
                                        ${(session.exercises ?? [])
                                            .map(
                                                exercise => `
                                                    <div class="tr-day-exercise">
                                                        <div class="tr-ex-name">
                                                            ${getDayExerciseName(
                                                                exercise
                                                            )}
                                                        </div>
                                                        <div class="tr-ex-meta">
                                                            ${
                                                                exercise.load != null
                                                                    ? t(
                                                                        "heatmap.exerciseMeta",
                                                                        {
                                                                            sets: exercise.sets,
                                                                            reps: exercise.reps,
                                                                            load: exercise.load
                                                                        }
                                                                    )
                                                                    : t(
                                                                        "heatmap.exerciseMetaNoLoad",
                                                                        {
                                                                            sets: exercise.sets,
                                                                            reps: exercise.reps
                                                                        }
                                                                    )
                                                            }
                                                        </div>
                                                    </div>
                                                `
                                            )
                                            .join("")}
                                    </div>
                                `
                            )
                            .join("");
                }

                modal.classList.add(
                    "open"
                );
            }
        )
        .catch(() => {
            const modal =
                document.getElementById(
                    "tr-day-details-modal"
                );

            const title =
                document.getElementById(
                    "tr-day-details-title"
                );

            const body =
                document.getElementById(
                    "tr-day-details-body"
                );

            if (title) {
                title.textContent =
                    t(
                        "heatmap.error"
                    );
            }

            if (body) {
                body.innerHTML =
                    `<p>${t(
                        "heatmap.loadError"
                    )}</p>`;
            }

            modal?.classList.add(
                "open"
            );
        });
}
