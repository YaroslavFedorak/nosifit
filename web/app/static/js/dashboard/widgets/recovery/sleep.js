function getElement(id) {
    return document.getElementById(id);
}
function formatDuration(minutes) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours} год ${remainingMinutes} хв`;
}
function formatTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "—";
    }
    return date.toLocaleTimeString("uk-UA", {
        hour: "2-digit",
        minute: "2-digit"
    });
}
function getSleepStatus(minutes) {
    if (minutes <= 0) {
        return "Немає даних";
    }
    if (minutes >= 480) {
        return "Відмінний сон";
    }
    if (minutes >= 420) {
        return "Добрий сон";
    }
    if (minutes >= 360) {
        return "Достатній сон";
    }
    return "Недосип";
}
function getRecencyLabel(dateValue) {
    if (!dateValue) {
        return "";
    }
    const snapshotDate = new Date(dateValue);
    if (Number.isNaN(snapshotDate.getTime())) {
        return "";
    }
    const today = new Date();
    const snapshotDay = new Date(snapshotDate.getFullYear(), snapshotDate.getMonth(), snapshotDate.getDate());
    const todayDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const difference = Math.round((todayDay.getTime() - snapshotDay.getTime()) /
        (1000 * 60 * 60 * 24));
    if (difference === 0) {
        return "Останній запис: сьогодні";
    }
    if (difference === 1) {
        return "Останній запис: вчора";
    }
    return `Останній запис: ${snapshotDate.toLocaleDateString("uk-UA", {
        day: "numeric",
        month: "long",
        year: "numeric"
    })}`;
}
export function renderSleep(snapshot) {
    const durationEl = getElement("dashboard-sleep-duration");
    const rangeEl = getElement("dashboard-sleep-range");
    const qualityEl = getElement("dashboard-sleep-quality");
    const metaEl = getElement("dashboard-sleep-meta");
    if (!durationEl || !rangeEl || !qualityEl || !metaEl) {
        return;
    }
    if (!snapshot ||
        snapshot.sleep_duration_minutes == null ||
        !snapshot.sleep_start ||
        !snapshot.sleep_end) {
        durationEl.textContent = "Немає даних";
        rangeEl.textContent = "Додайте сон для відстеження";
        qualityEl.textContent = "Немає даних";
        metaEl.textContent = "";
        return;
    }
    const duration = Number(snapshot.sleep_duration_minutes);
    if (!Number.isFinite(duration) || duration <= 0) {
        durationEl.textContent = "Немає даних";
        rangeEl.textContent = "Додайте сон для відстеження";
        qualityEl.textContent = "Немає даних";
        metaEl.textContent = "";
        return;
    }
    durationEl.textContent = formatDuration(duration);
    rangeEl.textContent =
        `${formatTime(snapshot.sleep_start)} → ${formatTime(snapshot.sleep_end)}`;
    qualityEl.textContent = getSleepStatus(duration);
    metaEl.textContent = getRecencyLabel(snapshot.date);
}
export function initSleepButton() {
    const button = getElement("dashboard-add-sleep");
    if (!button) {
        return;
    }
    button.addEventListener("click", () => {
        const recoveryButton = getElement("dashboard-open-recovery");
        recoveryButton?.click();
    });
}
