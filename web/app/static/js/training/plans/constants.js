export const DAYS = [
    { key: "mon", short: "Пн" },
    { key: "tue", short: "Вт" },
    { key: "wed", short: "Ср" },
    { key: "thu", short: "Чт" },
    { key: "fri", short: "Пт" },
    { key: "sat", short: "Сб" },
    { key: "sun", short: "Нд" }
];
export function isPlanDayKey(value) {
    return DAYS.some(day => day.key === value);
}
