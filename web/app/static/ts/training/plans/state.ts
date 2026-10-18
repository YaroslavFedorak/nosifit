import {
    defaultPrescription,
    isDurationExercise
} from "../measurement.js";

import type {
    GeneratedPlan,
    PlanDayKey,
    PlanDays,
    PlanExercise,
    PlanLocation,
    PlanWeek,
    RawPlanDays
} from "../api.js";

import {
    trainingStore
} from "../store.js";

import {
    DAYS
} from "./constants.js";

// Where a day is trained and what is at hand; equipment null = no limit.
export type DayMeta = {
    location: PlanLocation | null;
    equipment: string[] | null;
};

export type PlanState = {
    days: PlanDays;
    meta: Record<PlanDayKey, DayMeta>;
    currentDay: PlanDayKey;
    week: PlanWeek | null;
    generated: GeneratedPlan | null;
};

function emptyMeta(): Record<PlanDayKey, DayMeta> {
    const meta = {} as Record<PlanDayKey, DayMeta>;

    DAYS.forEach(day => {
        meta[day.key] = {
            location: null,
            equipment: null
        };
    });

    return meta;
}

export const state: PlanState = {
    days: {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    },
    meta: emptyMeta(),
    currentDay: "mon",
    week: null,
    generated: null
};

function dayExercises(
    value: RawPlanDays[PlanDayKey]
): PlanExercise[] {
    if (Array.isArray(value)) {
        return value;
    }

    return Array.isArray(value?.exercises)
        ? value.exercises
        : [];
}

export function normalizeMeta(
    days: RawPlanDays | null | undefined
): Record<PlanDayKey, DayMeta> {
    const meta = emptyMeta();

    DAYS.forEach(day => {
        const value = days?.[day.key];

        if (
            !value ||
            Array.isArray(value)
        ) {
            return;
        }

        meta[day.key] = {
            location:
                value.location ?? null,
            equipment:
                Array.isArray(value.equipment)
                    ? [...value.equipment]
                    : null
        };
    });

    return meta;
}

// The payload the API stores. location and equipment are always sent, null
// included: the server keeps what it has for a day that omits them.
export function serializeDays(): Record<string, unknown> {
    const result: Record<string, unknown> = {};

    DAYS.forEach(day => {
        const meta = state.meta[day.key];

        result[day.key] = {
            exercises: state.days[day.key],
            location: meta.location,
            equipment: meta.equipment
        };
    });

    return result;
}

export function normalize(
    days: RawPlanDays | null | undefined
): PlanDays {
    const normalized: PlanDays = {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    };

    if (
        !days ||
        typeof days !== "object"
    ) {
        return normalized;
    }

    DAYS.forEach(day => {
        normalized[day.key] = dayExercises(days[day.key])
            .filter(
                item =>
                    item &&
                    typeof item === "object" &&
                    "exercise" in item
            )
            .map(item => ({
                exercise: item.exercise,
                sets: Number(item.sets) || 0,
                ...(isDurationExercise(item.exercise)
                    ? {
                        reps: null,
                        duration_sec:
                            Number(item.duration_sec) ||
                            defaultPrescription(item.exercise).duration_sec
                    }
                    : {
                        reps:
                            item.reps ||
                            defaultPrescription(item.exercise).reps,
                        duration_sec: null
                    }),
                load: Number(item.load) || 0
            }));
    });

    return normalized;
}

function createEmptyDays(): PlanDays {
    return {
        mon: [],
        tue: [],
        wed: [],
        thu: [],
        fri: [],
        sat: [],
        sun: []
    };
}

export function initState(
    reset = false
): void {
    if (
        !reset &&
        trainingStore.plan?.days
    ) {
        state.days = normalize(
            trainingStore.plan.days
        );

        state.meta = normalizeMeta(
            trainingStore.plan.days
        );

        state.currentDay = "mon";

        return;
    }

    if (!reset) {
        return;
    }

    state.days = createEmptyDays();
    state.meta = emptyMeta();
    state.week = null;
    state.generated = null;
    state.currentDay = "mon";
}

// Fill the editor from the saved plan (or empty it when there is none).
export function loadStateFromPlan(): void {
    const days =
        trainingStore.plan?.days;

    state.days = normalize(days);
    state.meta = normalizeMeta(days);
    state.week = null;
    state.generated = null;
    state.currentDay = "mon";
}

export function getCurrentDayExercises(): PlanExercise[] {
    return state.days[
        state.currentDay
    ] ?? [];
}