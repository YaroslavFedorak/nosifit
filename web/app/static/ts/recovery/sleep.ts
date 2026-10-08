import {
getLocale,
translate
} from "../i18n/loader.js";

import {
RECOVERY_MESSAGES
} from "./messages.js";

import {
clearElement,
createCard,
createEmpty,
createError,
createLoading
} from "./dom.js";

import {
ICONS
} from "../icons/index.js";

interface SleepSnapshot {
sleep_duration_minutes?: number | null;
sleep_start?: string | null;
sleep_end?: string | null;
date?: string | null;
}

interface RenderOptions {
loading?: boolean;
error?: string | null;
}

function getSleepStatus(
minutes: number | null | undefined
): string {
if (
!minutes ||
minutes <= 0
) {
return translate(
"recovery",
"sleep.status.none"
);
}

if (
    minutes >= 480
) {
    return translate(
        "recovery",
        "sleep.status.excellent"
    );
}

if (
    minutes >= 420
) {
    return translate(
        "recovery",
        "sleep.status.good"
    );
}

if (
    minutes >= 360
) {
    return translate(
        "recovery",
        "sleep.status.sufficient"
    );
}

return translate(
    "recovery",
    "sleep.status.insufficient"
);

}

function getDateKey(
date: Date
): string {
return [
date.getFullYear(),
String(
date.getMonth() + 1
).padStart(2, "0"),
String(
date.getDate()
).padStart(2, "0")
].join("-");
}

function getRecencyLabel(
snapshotDateIso?: string | null
): string {
if (!snapshotDateIso) {
return "";
}

const snapshotDate =
    new Date(
        snapshotDateIso
    );

if (
    Number.isNaN(
        snapshotDate.getTime()
    )
) {
    return "";
}

const today =
    new Date();

const snapshotKey =
    getDateKey(
        snapshotDate
    );

const todayKey =
    getDateKey(
        today
    );

if (
    snapshotKey ===
    todayKey
) {
    return translate(
        "recovery",
        "sleep.recency.today"
    );
}

const yesterday =
    new Date(
        today
    );

yesterday.setDate(
    yesterday.getDate() - 1
);

if (
    snapshotKey ===
    getDateKey(
        yesterday
    )
) {
    return translate(
        "recovery",
        "sleep.recency.yesterday"
    );
}

const date =
    snapshotDate.toLocaleDateString(
        getLocale(),
        {
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    );

return translate(
    "recovery",
    "sleep.recency.date",
    {
        date
    }
);

}

export function renderSleepWidget(
snapshot: SleepSnapshot | null,
options: RenderOptions = {}
): void {
const el =
document.getElementById(
"sleep-widget"
);

if (!el) {
    return;
}

clearElement(el);

if (options.loading) {
    el.appendChild(
        createLoading(
            RECOVERY_MESSAGES.loading
        )
    );

    return;
}

if (options.error) {
    el.appendChild(
        createError(
            RECOVERY_MESSAGES.error
        )
    );

    return;
}

if (
    !snapshot ||
    snapshot.sleep_duration_minutes == null ||
    !snapshot.sleep_start ||
    !snapshot.sleep_end
) {
    el.appendChild(
        createEmpty(
            RECOVERY_MESSAGES.sleep.empty
        )
    );

    return;
}

const card =
    createCard(
        "sleep-card"
    );

const content =
    document.createElement(
        "div"
    );

content.className =
    "sleep-content";

const durationHours =
    Math.floor(
        snapshot.sleep_duration_minutes /
        60
    );

const durationMinutes =
    snapshot.sleep_duration_minutes %
    60;

const start =
    new Date(
        snapshot.sleep_start
    );

const end =
    new Date(
        snapshot.sleep_end
    );

const startStr =
    start.toLocaleTimeString(
        getLocale(),
        {
            hour: "2-digit",
            minute: "2-digit"
        }
    );

const endStr =
    end.toLocaleTimeString(
        getLocale(),
        {
            hour: "2-digit",
            minute: "2-digit"
        }
    );

const statusText =
    getSleepStatus(
        snapshot.sleep_duration_minutes
    );

const recencyText =
    getRecencyLabel(
        snapshot.date
    );

const top =
    document.createElement(
        "div"
    );

top.className =
    "sleep-top";

const left =
    document.createElement(
        "div"
    );

left.className =
    "sleep-top-left";

const durationEl =
    document.createElement(
        "div"
    );

durationEl.className =
    "sleep-duration";

durationEl.textContent =
    `${durationHours} ${translate(
        "recovery",
        "sleep.duration.hours"
    )} ${durationMinutes} ${translate(
        "recovery",
        "sleep.duration.minutes"
    )}`;

const rangeEl =
    document.createElement(
        "div"
    );

rangeEl.className =
    "sleep-range";

rangeEl.textContent =
    `${startStr} → ${endStr}`;

left.appendChild(
    durationEl
);

left.appendChild(
    rangeEl
);

const icon =
    document.createElement(
        "div"
    );

icon.className =
    "sleep-icon";

icon.innerHTML =
    ICONS.moon || "";

top.appendChild(
    left
);

top.appendChild(
    icon
);

const bottom =
    document.createElement(
        "div"
    );

bottom.className =
    "sleep-bottom";

const statusEl =
    document.createElement(
        "div"
    );

statusEl.className =
    "sleep-status";

statusEl.textContent =
    statusText;

const metaEl =
    document.createElement(
        "div"
    );

metaEl.className =
    "sleep-meta";

metaEl.textContent =
    recencyText;

bottom.appendChild(
    statusEl
);

bottom.appendChild(
    metaEl
);

content.appendChild(
    top
);

content.appendChild(
    bottom
);

card.appendChild(
    content
);

el.appendChild(
    card
);

}
