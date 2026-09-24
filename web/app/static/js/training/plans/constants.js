export const DAYS = [
    { key: "mon" },
    { key: "tue" },
    { key: "wed" },
    { key: "thu" },
    { key: "fri" },
    { key: "sat" },
    { key: "sun" }
];
export function isPlanDayKey(value) {
    return DAYS.some(day => day.key === value);
}
