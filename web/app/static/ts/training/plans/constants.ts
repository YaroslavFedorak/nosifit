import type { PlanDayKey } from "../api.js";

export const DAYS: {
    key: PlanDayKey;
}[] = [
    { key: "mon" },
    { key: "tue" },
    { key: "wed" },
    { key: "thu" },
    { key: "fri" },
    { key: "sat" },
    { key: "sun" }
];

export function isPlanDayKey(
    value: string
): value is PlanDayKey {
    return DAYS.some(
        day => day.key === value
    );
}