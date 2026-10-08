const DEFAULT_SETS = 3;
const DEFAULT_REPS = "8-12";
const DEFAULT_SECONDS = 30;
export function isDurationExercise(exercise) {
    return exercise?.measurement_type === "duration";
}
export function isPerSide(exercise) {
    return exercise?.prescription?.per_side === true;
}
export function defaultPrescription(exercise) {
    const prescription = exercise?.prescription ?? {};
    const sets = Number(prescription.sets) || DEFAULT_SETS;
    if (isDurationExercise(exercise)) {
        const low = Number(prescription.seconds_min);
        const high = Number(prescription.seconds_max);
        const seconds = low && high
            ? Math.round((low + high) / 2 / 5) * 5
            : DEFAULT_SECONDS;
        return {
            sets,
            reps: null,
            duration_sec: seconds,
            per_side: isPerSide(exercise)
        };
    }
    const low = Number(prescription.reps_min);
    const high = Number(prescription.reps_max);
    const reps = low && high
        ? low === high
            ? String(low)
            : `${low}-${high}`
        : DEFAULT_REPS;
    return {
        sets,
        reps,
        duration_sec: null,
        per_side: isPerSide(exercise)
    };
}
// Muscle slugs behind each exercise-picker category.
export const MUSCLE_CATEGORIES = {
    chest: ["chest"],
    back: ["lats", "upper-back", "traps", "lower-back"],
    legs: ["quads", "hamstrings", "glutes", "adductors", "calves"],
    shoulders: ["shoulders"],
    arms: ["biceps", "triceps", "forearms"],
    core: ["core", "abs", "obliques"]
};
