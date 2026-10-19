import type {
    Exercise
} from "../api.js";

import {
    trainingStore
} from "../store.js";

import {
    OUTDOOR_EQUIPMENT
} from "./constants.js";

import type {
    DayMeta
} from "./state.js";

// Equipment a day can use, or null when it is not limited. Mirrors
// plan_days.available_equipment on the server (which has the last word).
export function allowedEquipment(
    meta: DayMeta
): Set<string> | null {
    if (meta.equipment === null) {
        return null;
    }

    const allowed = new Set(
        meta.equipment
    );

    allowed.add("bodyweight");

    if (meta.location === "outdoors") {
        [...allowed].forEach(
            slug => {
                if (
                    slug !== "bodyweight" &&
                    !OUTDOOR_EQUIPMENT.includes(slug)
                ) {
                    allowed.delete(slug);
                }
            }
        );
    }

    return allowed;
}

export function equipmentOf(
    exercise: Pick<Exercise, "id"> & Partial<Exercise>
): string[] {
    const known =
        exercise.equipment ??
        trainingStore.exercises.find(
            item =>
                String(item.id) ===
                String(exercise.id)
        )?.equipment;

    return (known ?? []).filter(
        slug => slug !== "bodyweight"
    );
}

export function missingEquipment(
    exercise: Pick<Exercise, "id"> & Partial<Exercise>,
    allowed: Set<string> | null
): string[] {
    if (allowed === null) {
        return [];
    }

    return equipmentOf(exercise).filter(
        slug => !allowed.has(slug)
    );
}
