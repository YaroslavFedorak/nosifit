import { trainingAPI } from "./api.js";

let isSavingWorkout = false;

function normalizeDatabaseId(value) {
    if (!value) return null;
    return String(value);
}

function prepareExerciseForSave(exercise = {}) {
    const databaseId = normalizeDatabaseId(
        exercise.databaseId ??
        exercise.database_id ??
        exercise.exerciseId ??
        exercise.exercise_id ??
        exercise.original?.id ??
        exercise.exercise?.id
    );

    return {
        ...exercise,
        databaseId
    };
}

function isValidExercise(exercise) {
    const hasDatabaseId = exercise.databaseId !== null;
    const hasName = typeof exercise.name === "string" && exercise.name.trim().length > 0;
    const hasSets = Number(exercise.sets) > 0;
    const hasReps =
        exercise.reps !== null &&
        exercise.reps !== undefined &&
        String(exercise.reps).trim() !== "";
    return hasDatabaseId && hasName && hasSets && hasReps;
}

function getWorkoutTitle() {
    const titleInput = document.getElementById("dashboard-workout-title");
    return titleInput?.value?.trim() || "Тренування";
}

function clearWorkoutTitle() {
    const titleInput = document.getElementById("dashboard-workout-title");
    if (titleInput) {
        titleInput.value = "";
    }
}

function getSaveButton() {
    return document.getElementById("dashboard-save-workout");
}

function setSaveState(isSaving) {
    const button = getSaveButton();
    if (button) {
        button.disabled = isSaving;
    }
}

function getFatigueBefore() {
    return document.body.dataset.fatigueBefore || null;
}

function getFatigueAfter() {
    return document.body.dataset.fatigueAfter || null;
}

function prepareExercises(exercises) {
    return exercises.map(prepareExerciseForSave).filter(isValidExercise);
}

function persistExercises(exercises) {
    try {
        const serialized = JSON.stringify(exercises);
        const today = new Date().toISOString().slice(0, 10);

        window.localStorage.setItem("dashboard_training_exercises", serialized);
        window.localStorage.setItem("dashboard_training_date", today);
    } catch (_) {}
}

async function saveExercise(sessionId, exercise) {
    await trainingAPI.addExerciseToSession(sessionId, exercise.databaseId);
    await trainingAPI.updateSessionExercise(sessionId, exercise.databaseId, {
        sets_done: Number(exercise.sets),
        reps_done: String(exercise.reps),
        load_done: Number(exercise.weight ?? exercise.load ?? 0),
        rpe: exercise.rpe != null ? Number(exercise.rpe) : null
    });
}

async function saveExercises(sessionId, exercises) {
    let savedExercises = 0;
    for (const exercise of exercises) {
        await saveExercise(sessionId, exercise);
        savedExercises += 1;
    }
    return savedExercises;
}

export async function saveWorkout({ exercises, onSuccess }) {
    if (isSavingWorkout) {
        return null;
    }

    if (!Array.isArray(exercises) || !exercises.length) {
        throw new Error("Позначте хоча б одну виконану вправу.");
    }

    const validExercises = prepareExercises(exercises);

    if (!validExercises.length) {
        throw new Error("Немає коректних вправ для збереження.");
    }

    isSavingWorkout = true;
    setSaveState(true);

    try {
        const title = getWorkoutTitle();

        const sessionResponse = await trainingAPI.startTrainingSession({
            title,
            fatigue_before: getFatigueBefore()
        });

        const session = sessionResponse?.session ?? sessionResponse;
        const sessionId = normalizeDatabaseId(session?.id);

        if (sessionId === null) {
            throw new Error("Сервер не повернув коректний ID тренування.");
        }

        persistExercises(validExercises);

        const savedExercises = await saveExercises(sessionId, validExercises);

        if (savedExercises === 0) {
            throw new Error("Не вдалося зберегти жодної вправи.");
        }

        const finished = await trainingAPI.finishTrainingSession(sessionId, {
            fatigue_after: getFatigueAfter()
        });

        clearWorkoutTitle();

        if (typeof onSuccess === "function") {
            await onSuccess(finished);
        }

        return finished;
    } finally {
        isSavingWorkout = false;
        setSaveState(false);
    }
}
