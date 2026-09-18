import type {
HeatmapData,
HeatmapDay,
} from "../../heatmap/render";

const MONTHS = [
"Січень",
"Лютий",
"Березень",
"Квітень",
"Травень",
"Червень",
"Липень",
"Серпень",
"Вересень",
"Жовтень",
"Листопад",
"Грудень",
];

const WEEKDAYS = [
"Пн",
"Вт",
"Ср",
"Чт",
"Пт",
"Сб",
"Нд",
];

function formatDateKey(
date: Date,
): string {
const year =
date.getFullYear();

const month =
    String(
        date.getMonth() + 1,
    ).padStart(
        2,
        "0",
    );

const day =
    String(
        date.getDate(),
    ).padStart(
        2,
        "0",
    );

return `${year}-${month}-${day}`;

}

function getMondayOffset(
date: Date,
): number {
const day =
date.getDay();

return day === 0
    ? 6
    : day - 1;

}

function buildDayMap(
data: HeatmapData | null,
): Map<string, HeatmapDay> {
const map =
new Map<
string,
HeatmapDay
>();

if (
    !data ||
    !Array.isArray(
        data.days,
    )
) {
    return map;
}

data.days.forEach(
    (
        day,
    ) => {
        if (
            typeof day.date !==
            "string"
        ) {
            return;
        }

        map.set(
            day.date,
            day,
        );
    },
);

return map;

}

function createEmptyDay(
date: string,
): HeatmapDay {
return {
date,
daily_score: null,
level: 0,
training: {
score: null,
},
recovery: {
score: null,
},
nutrition: {
score: null,
},
};
}

function getLevel(
day: HeatmapDay,
): number {
return typeof day.level === "number"
? Math.max(
0,
Math.min(
6,
Math.round(
day.level,
),
),
)
: 0;
}

function createCalendarDay(
day: HeatmapDay,
month: number,
year: number,
): HTMLButtonElement {
const element =
document.createElement(
"button",
);

element.type =
    "button";

element.className =
    "heatmap-calendar-day";

const level =
    getLevel(
        day,
    );

element.dataset.level =
    String(level);

if (day.date) {
    element.dataset.date =
        day.date;
}

const date =
    day.date
        ? new Date(
            `${day.date}T12:00:00`,
        )
        : new Date(
            year,
            month,
            1,
        );

const todayKey =
    formatDateKey(
        new Date(),
    );

if (
    day.date === todayKey
) {
    element.classList.add(
        "is-today",
    );
}

element.setAttribute(
    "aria-label",
    day.date
        ? `${date.getDate()} ${MONTHS[month]} ${year}`
        : "Немає даних",
);

const number =
    document.createElement(
        "span",
    );

number.className =
    "heatmap-calendar-day-number";

number.textContent =
    String(
        date.getDate(),
    );

element.appendChild(
    number,
);

if (day.date) {
    element.addEventListener(
        "click",
        () => {
            document.dispatchEvent(
                new CustomEvent(
                    "dashboard:open-day",
                    {
                        detail: day,
                    },
                ),
            );
        },
    );
} else {
    element.disabled =
        true;
}

return element;

}

function createEmptyCell(): HTMLDivElement {
const empty =
document.createElement(
"div",
);

empty.className =
    "heatmap-calendar-day is-empty";

empty.setAttribute(
    "aria-hidden",
    "true",
);

return empty;

}

function createCalendar(
year: number,
month: number,
dayMap: Map<string, HeatmapDay>,
onMonthChange: (
year: number,
month: number,
) => void,
): HTMLElement {
const wrapper =
document.createElement(
"div",
);

wrapper.className =
    "heatmap-calendar";

const navigation =
    document.createElement(
        "div",
    );

navigation.className =
    "heatmap-calendar-navigation";

const previous =
    document.createElement(
        "button",
    );

previous.type =
    "button";

previous.className =
    "heatmap-calendar-nav-button";

previous.setAttribute(
    "aria-label",
    "Попередній місяць",
);

previous.textContent =
    "‹";

previous.addEventListener(
    "click",
    () => {
        onMonthChange(
            year,
            month - 1,
        );
    },
);

const title =
    document.createElement(
        "h3",
    );

title.className =
    "heatmap-calendar-month";

title.textContent =
    `${MONTHS[month]} ${year}`;

const next =
    document.createElement(
        "button",
    );

next.type =
    "button";

next.className =
    "heatmap-calendar-nav-button";

next.setAttribute(
    "aria-label",
    "Наступний місяць",
);

next.textContent =
    "›";

next.addEventListener(
    "click",
    () => {
        onMonthChange(
            year,
            month + 1,
        );
    },
);

navigation.append(
    previous,
    title,
    next,
);

const weekdays =
    document.createElement(
        "div",
    );

weekdays.className =
    "heatmap-calendar-weekdays";

WEEKDAYS.forEach(
    (
        weekday,
    ) => {
        const element =
            document.createElement(
                "span",
            );

        element.className =
            "heatmap-calendar-weekday";

        element.textContent =
            weekday;

        weekdays.appendChild(
            element,
        );
    },
);

const grid =
    document.createElement(
        "div",
    );

grid.className =
    "heatmap-calendar-grid";

const firstDate =
    new Date(
        year,
        month,
        1,
    );

const daysInMonth =
    new Date(
        year,
        month + 1,
        0,
    ).getDate();

const offset =
    getMondayOffset(
        firstDate,
    );

for (
    let index = 0;
    index < offset;
    index += 1
) {
    grid.appendChild(
        createEmptyCell(),
    );
}

for (
    let dayNumber = 1;
    dayNumber <= daysInMonth;
    dayNumber += 1
) {
    const date =
        new Date(
            year,
            month,
            dayNumber,
        );

    const dateKey =
        formatDateKey(
            date,
        );

    const day =
        dayMap.get(
            dateKey,
        ) ??
        createEmptyDay(
            dateKey,
        );

    grid.appendChild(
        createCalendarDay(
            day,
            month,
            year,
        ),
    );
}

const legend =
    document.createElement(
        "div",
    );

legend.className =
    "heatmap-calendar-legend";

const less =
    document.createElement(
        "span",
    );

less.textContent =
    "Менше";

legend.appendChild(
    less,
);

for (
    let level = 0;
    level <= 6;
    level += 1
) {
    const box =
        document.createElement(
            "span",
        );

    box.className =
        "heatmap-calendar-legend-box";

    box.classList.add(
        `l${level}`,
    );

    legend.appendChild(
        box,
    );
}

const more =
    document.createElement(
        "span",
    );

more.textContent =
    "Більше";

legend.appendChild(
    more,
);

wrapper.append(
    navigation,
    weekdays,
    grid,
    legend,
);

return wrapper;

}

function setModalState(
modal: HTMLElement,
open: boolean,
): void {
modal.classList.toggle(
"open",
open,
);

modal.setAttribute(
    "aria-hidden",
    String(!open),
);

}

export function openCalendarModal(
data: HeatmapData | null,
): void {
const modal =
document.getElementById(
"dashboard-calendar-modal",
);

const content =
    document.getElementById(
        "dashboard-calendar-content",
    );

if (
    !modal ||
    !content
) {
    return;
}

const dayMap =
    buildDayMap(
        data,
    );

const now =
    new Date();

let currentYear =
    now.getFullYear();

let currentMonth =
    now.getMonth();

const render =
    (): void => {
        content.innerHTML =
            "";

        const calendar =
            createCalendar(
                currentYear,
                currentMonth,
                dayMap,
                (
                    year,
                    month,
                ) => {
                    const nextDate =
                        new Date(
                            year,
                            month,
                            1,
                        );

                    currentYear =
                        nextDate.getFullYear();

                    currentMonth =
                        nextDate.getMonth();

                    render();
                },
            );

        content.appendChild(
            calendar,
        );
    };

render();

setModalState(
    modal,
    true,
);

}

export function closeCalendarModal(): void {
const modal =
document.getElementById(
"dashboard-calendar-modal",
);

if (!modal) {
    return;
}

setModalState(
    modal,
    false,
);

}

export function initCalendarModal(
data: HeatmapData | null,
): void {
const modal =
document.getElementById(
"dashboard-calendar-modal",
);

if (!modal) {
    return;
}

modal
    .querySelectorAll<HTMLElement>(
        "[data-modal-close]",
    )
    .forEach(
        (
            element,
        ) => {
            element.addEventListener(
                "click",
                closeCalendarModal,
            );
        },
    );

const openButton =
    document.getElementById(
        "dashboard-open-calendar",
    );

openButton?.addEventListener(
    "click",
    () => {
        openCalendarModal(
            data,
        );
    },
);

}
