import { TrainingAPI } from "../widgets/training/api.js";
const state = {
    exercises: [],
    category: "all",
    search: "",
    callback: null,
    loading: false
};
function getModal() {
    return document.getElementById("db-exercise-modal");
}
function getList() {
    return document.getElementById("db-exercise-list");
}
function createLocalId() {
    return typeof crypto !==
        "undefined" &&
        typeof crypto.randomUUID ===
            "function"
        ? crypto.randomUUID()
        : Date.now().toString(36) +
            Math.random()
                .toString(36)
                .slice(2);
}
function normalizeDatabaseId(value) {
    return value
        ? String(value)
        : null;
}
function findExerciseId(exercise) {
    const candidates = [
        exercise?.id,
        exercise?.exercise_id,
        exercise?.exerciseId,
        exercise?.database_id,
        exercise?.databaseId,
        exercise?.exercise?.id,
        exercise?.exercise?.exercise_id,
        exercise?.exercise?.exerciseId,
        exercise?.exercise?.database_id,
        exercise?.exercise?.databaseId,
        exercise?.data?.id,
        exercise?.data?.exercise_id,
        exercise?.data?.exerciseId,
        exercise?.data?.database_id,
        exercise?.data?.databaseId
    ];
    for (const candidate of candidates) {
        const id = normalizeDatabaseId(candidate);
        if (id !== null) {
            return id;
        }
    }
    return null;
}
function normalizeArray(value) {
    if (Array.isArray(value)) {
        return value;
    }
    if (typeof value === "string" &&
        value.trim()) {
        return value
            .split(",")
            .map(item => item.trim())
            .filter(Boolean);
    }
    return [];
}
function normalizeExercise(exercise) {
    return {
        id: createLocalId(),
        databaseId: findExerciseId(exercise),
        name: String(exercise?.name ??
            exercise?.exercise_name ??
            exercise?.title ??
            exercise?.exercise?.name ??
            "Без назви"),
        movement_pattern: exercise?.movement_pattern ??
            exercise?.movementPattern ??
            exercise?.exercise
                ?.movement_pattern ??
            exercise?.exercise
                ?.movementPattern ??
            "",
        muscles_primary: normalizeArray(exercise?.muscles_primary ??
            exercise?.primary_muscles ??
            exercise?.exercise
                ?.muscles_primary ??
            exercise?.exercise
                ?.primary_muscles),
        muscles_secondary: normalizeArray(exercise?.muscles_secondary ??
            exercise?.secondary_muscles ??
            exercise?.exercise
                ?.muscles_secondary ??
            exercise?.exercise
                ?.secondary_muscles),
        equipment: normalizeArray(exercise?.equipment ??
            exercise?.exercise?.equipment),
        original: exercise
    };
}
function openModal() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("db-modal-open");
}
function closeModal() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("db-modal-open");
    state.callback = null;
}
function matchesCategory(exercise) {
    if (state.category === "all") {
        return true;
    }
    const category = state.category.toLowerCase();
    const pattern = (exercise.movement_pattern ||
        "").toLowerCase();
    const muscles = [
        ...exercise.muscles_primary,
        ...exercise.muscles_secondary
    ].map(muscle => muscle.toLowerCase());
    if (category === "legs") {
        return (pattern.includes("squat") ||
            pattern.includes("lunge") ||
            muscles.some(muscle => muscle.includes("quad") ||
                muscle.includes("glute") ||
                muscle.includes("hamstring") ||
                muscle.includes("calf")));
    }
    if (category === "core") {
        return (pattern.includes("core") ||
            pattern.includes("abs") ||
            muscles.some(muscle => muscle.includes("abs") ||
                muscle.includes("oblique")));
    }
    if (category === "mobility") {
        return (pattern.includes("mobility") ||
            pattern.includes("stretch"));
    }
    return (pattern.includes(category) ||
        muscles.some(muscle => muscle.includes(category)));
}
function getFilteredExercises() {
    const query = state.search
        .trim()
        .toLowerCase();
    return state.exercises.filter(exercise => {
        const name = exercise.name.toLowerCase();
        return ((!query ||
            name.includes(query)) &&
            matchesCategory(exercise));
    });
}
function renderEmpty(message) {
    const list = getList();
    if (!list) {
        return;
    }
    list.innerHTML =
        `<div class="db-session-empty">${message}</div>`;
}
function renderExercises() {
    const list = getList();
    if (!list) {
        return;
    }
    list.innerHTML = "";
    if (state.loading) {
        renderEmpty("Завантаження вправ...");
        return;
    }
    const items = getFilteredExercises();
    if (!items.length) {
        renderEmpty("Вправи не знайдені.");
        return;
    }
    const fragment = document.createDocumentFragment();
    items.forEach(exercise => {
        const button = document.createElement("button");
        button.type = "button";
        button.className =
            "db-session-item";
        if (exercise.databaseId) {
            button.dataset.exerciseId =
                exercise.databaseId;
        }
        const name = document.createElement("div");
        name.className =
            "db-session-item-name";
        name.textContent =
            exercise.name;
        button.appendChild(name);
        button.addEventListener("click", () => {
            if (!state.callback) {
                return;
            }
            state.callback({
                databaseId: exercise.databaseId,
                id: exercise.databaseId,
                name: exercise.name,
                movement_pattern: exercise.movement_pattern,
                muscles_primary: exercise.muscles_primary,
                muscles_secondary: exercise.muscles_secondary,
                equipment: exercise.equipment,
                sets: 3,
                reps: "10",
                weight: 0,
                completed: false
            });
            closeModal();
        });
        fragment.appendChild(button);
    });
    list.appendChild(fragment);
}
function extractExercises(data) {
    if (Array.isArray(data?.items)) {
        return data.items;
    }
    if (Array.isArray(data?.exercises)) {
        return data.exercises;
    }
    if (Array.isArray(data)) {
        return data;
    }
    return [];
}
async function loadExercises() {
    state.loading = true;
    renderExercises();
    try {
        const data = await TrainingAPI.getExercises();
        const raw = extractExercises(data);
        state.exercises =
            raw
                .map(normalizeExercise)
                .filter(exercise => exercise.databaseId !==
                null &&
                exercise.name !==
                    "Без назви");
        console.log("Dashboard exercises loaded:", state.exercises.length);
    }
    catch (error) {
        console.error("Failed to load dashboard exercises:", error);
        state.exercises = [];
        renderEmpty("Не вдалося завантажити вправи.");
    }
    finally {
        state.loading = false;
        renderExercises();
    }
}
export function openExerciseModal(callback) {
    state.callback =
        typeof callback === "function"
            ? callback
            : null;
    openModal();
    void loadExercises();
}
export function closeExerciseModal() {
    closeModal();
}
export function initExerciseModal() {
    const modal = getModal();
    if (!modal) {
        return;
    }
    const search = document.getElementById("db-exercise-search");
    const filters = modal.querySelectorAll("[data-exercise-category]");
    if (search) {
        search.addEventListener("input", () => {
            state.search =
                search.value;
            renderExercises();
        });
    }
    filters.forEach(button => {
        button.addEventListener("click", () => {
            state.category =
                button.dataset
                    .exerciseCategory ||
                    "all";
            filters.forEach(filter => filter.classList.remove("active"));
            button.classList.add("active");
            renderExercises();
        });
    });
    modal
        .querySelectorAll("[data-close-exercise-modal]")
        .forEach(button => {
        button.addEventListener("click", closeModal);
    });
    modal.addEventListener("click", event => {
        if (event.target ===
            modal) {
            closeModal();
        }
    });
}
