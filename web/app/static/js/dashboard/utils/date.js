export function formatDashboardDate(value) {
    const date = value instanceof Date
        ? value
        : new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) {
        return "—";
    }
    return new Intl.DateTimeFormat("uk-UA", {
        weekday: "long",
        day: "numeric",
        month: "long"
    }).format(date);
}
