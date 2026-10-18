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
export const LOCATIONS = [
    "home",
    "gym",
    "outdoors"
];
// Equipment slugs a day can list (bodyweight is always available). Kept in
// step with backend/app/training/data/equipment/equipment.json; the server
// validates every slug.
export const EQUIPMENT = [
    "barbell",
    "dumbbells",
    "bench",
    "machine",
    "cable",
    "bar",
    "dip-bars",
    "rings",
    "band",
    "kettlebell",
    "trap-bar",
    "landmine",
    "box",
    "sled",
    "medicine-ball",
    "stability-ball",
    "ab-wheel",
    "battle-rope",
    "jump-rope"
];
// What can be used outdoors; same list as the server's OUTDOOR_EQUIPMENT.
export const OUTDOOR_EQUIPMENT = [
    "bar",
    "dip-bars",
    "rings",
    "band",
    "jump-rope"
];
