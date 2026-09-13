import { DAYS } from "./constants.js";

export interface PlanExercise {
    exercise: any;
    sets: number;
    reps: string;
    load: number;
}

export interface PlanDays {
    [key: string]: PlanExercise[];
}

export interface Plan {
    id?: string | number | null;
    name?: string;
    days?: any;
    [key: string]: any;
}

export interface PlanState {
    planId: string | number | null;
    days: PlanDays;
    currentDay: string;
}

export const state: PlanState = {
    planId: null,
    days: {},
    currentDay: DAYS[0].key
};

function toNonNegativeNumber(
    value: any,
    fallback: number = 0
): number {
    const number = Number(value);

    return Number.isFinite(number)
        ? Math.max(0, number)
        : fallback;
}

function normalizeExercise(
    exercise: any = {}
): PlanExercise {
    return {
        exercise:
            exercise.exercise ??
            exercise,

        sets:
            toNonNegativeNumber(
                exercise.sets,
                3
            ),

        reps:
            String(
                exercise.reps ??
                "8-12"
            ),

        load:
            toNonNegativeNumber(
                exercise.load ??
                exercise.weight,
                0
            )
    };
}

export function normalizeDays(
    days: any = {}
): PlanDays {
    return DAYS.reduce(
        (
            normalized: PlanDays,
            day
        ) => {
            const rawDay =
                days?.[day.key];

            const exercises =
                Array.isArray(rawDay)
                    ? rawDay
                    : Array.isArray(
                        rawDay?.exercises
                    )
                        ? rawDay.exercises
                        : [];

            normalized[day.key] =
                exercises.map(
                    normalizeExercise
                );

            return normalized;
        },
        {}
    );
}

export function setPlan(
    plan: Plan | null = null
): void {
    state.planId =
        plan?.id ?? null;

    state.days =
        normalizeDays(
            plan?.days
        );

    state.currentDay =
        DAYS[0].key;
}

export function addExercise(
    exercise: any
): void {
    if (
        !state.days[
            state.currentDay
        ]
    ) {
        state.days[
            state.currentDay
        ] = [];
    }

    state.days[
        state.currentDay
    ].push(
        normalizeExercise({
            exercise
        })
    );
}

export function replaceExercise(
    index: number,
    exercise: any
): void {
    const exercises =
        state.days[
            state.currentDay
        ];

    const current =
        exercises?.[index];

    if (!current) {
        return;
    }

    exercises[index] = {
        ...current,
        exercise
    };
}

export function removeExercise(
    index: number
): void {
    const exercises =
        state.days[
            state.currentDay
        ];

    if (!exercises) {
        return;
    }

    exercises.splice(
        index,
        1
    );
}

export function moveExercise(
    fromIndex: number,
    toIndex: number
): void {
    const exercises =
        state.days[
            state.currentDay
        ];

    if (!exercises) {
        return;
    }

    const [exercise] =
        exercises.splice(
            fromIndex,
            1
        );

    if (exercise) {
        exercises.splice(
            toIndex,
            0,
            exercise
        );
    }
}

export function getCurrentExercises(): PlanExercise[] {
    return (
        state.days[
            state.currentDay
        ] || []
    );
}