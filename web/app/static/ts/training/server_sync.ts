import {
    TrainingAPI,
    WorkoutExercise
} from "./api.js";

import {
    trainingStore
} from "./store.js";

import {
    persistSessionId,
    persistWorkout
} from "./state.js";

import {
    renderWorkoutList
} from "./workout.js";

// Today's workout lives on the server: the Telegram bot logs into the same
// session. The page takes the server's exercises as the saved truth and
// keeps only what is local and not on the server yet (planned items, done
// but unsaved items), so a later save never drops exercises logged
// elsewhere.
export async function syncWorkoutWithServer(): Promise<void> {
    let session;

    try {
        session = (await TrainingAPI.getLoggedToday()).session;
    } catch {
        return;
    }

    if (!session) {
        return;
    }

    const serverItems: WorkoutExercise[] =
        session.exercises.map(row => {
            const exercise =
                trainingStore.exercises.find(
                    item =>
                        String(item.id) === String(row.id)
                ) ?? {
                    id: row.id,
                    name: row.name,
                    slug: row.slug,
                    measurement_type: row.measurement_type
                };

            return {
                exercise,
                sets: row.sets,
                reps: row.reps,
                duration_sec: row.duration_sec,
                load: row.load ?? 0,
                rpe: row.rpe,
                set_entries: row.set_entries,
                done: true,
                fromPlan: false
            };
        });

    const onServer =
        new Set(
            serverItems.map(item => String(item.exercise.id))
        );

    const localOnly =
        trainingStore.workout.filter(
            item => !onServer.has(String(item.exercise?.id))
        );

    trainingStore.sessionId = session.id;
    persistSessionId(session.id);

    trainingStore.workout = [
        ...localOnly.filter(item => !item.done),
        ...serverItems,
        ...localOnly.filter(item => item.done)
    ];

    persistWorkout(trainingStore.workout);
    renderWorkoutList();
}

export function initServerSync(): void {
    void syncWorkoutWithServer();

    document.addEventListener(
        "visibilitychange",
        () => {
            if (document.visibilityState === "visible") {
                void syncWorkoutWithServer();
            }
        }
    );
}
