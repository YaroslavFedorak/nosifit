import { TrainingAPI } from "../../training/api.js";

const state = {
    exercises: [],
    category: "all",
    search: "",
    callback: null,
    loading: false
};

const getModal = () => document.getElementById("db-exercise-modal");
const getList = () => document.getElementById("db-exercise-list");

const createLocalId = () =>
    typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2);

const normalizeDatabaseId = value => (value ? String(value) : null);

function findExerciseId(ex) {
    const candidates = [
        ex.id,
        ex.exercise_id,
        ex.exerciseId,
        ex.database_id,
        ex.databaseId,
        ex.exercise?.id,
        ex.exercise?.exercise_id,
        ex.exercise?.exerciseId,
        ex.exercise?.database_id,
        ex.exercise?.databaseId,
        ex.data?.id,
        ex.data?.exercise_id,
        ex.data?.exerciseId,
        ex.data?.database_id,
        ex.data?.databaseId
    ];
    for (const c of candidates) {
        const id = normalizeDatabaseId(c);
        if (id !== null) return id;
    }
    return null;
}

const normalizeArray = value =>
    Array.isArray(value)
        ? value
        : typeof value === "string" && value.trim()
        ? value.split(",").map(v => v.trim()).filter(Boolean)
        : [];

const normalizeExercise = ex => ({
    id: createLocalId(),
    databaseId: findExerciseId(ex),
    name: String(
        ex.name ??
        ex.exercise_name ??
        ex.title ??
        ex.exercise?.name ??
        "Без назви"
    ),
    movement_pattern:
        ex.movement_pattern ??
        ex.movementPattern ??
        ex.exercise?.movement_pattern ??
        ex.exercise?.movementPattern ??
        "",
    muscles_primary: normalizeArray(
        ex.muscles_primary ??
        ex.primary_muscles ??
        ex.exercise?.muscles_primary ??
        ex.exercise?.primary_muscles
    ),
    muscles_secondary: normalizeArray(
        ex.muscles_secondary ??
        ex.secondary_muscles ??
        ex.exercise?.muscles_secondary ??
        ex.exercise?.secondary_muscles
    ),
    equipment: normalizeArray(ex.equipment ?? ex.exercise?.equipment),
    original: ex
});

function openModal() {
    const modal = getModal();
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("db-modal-open");
}

function closeModal() {
    const modal = getModal();
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("db-modal-open");
    state.callback = null;
}

function matchesCategory(ex) {
    if (state.category === "all") return true;

    const cat = state.category.toLowerCase();
    const pattern = (ex.movement_pattern || "").toLowerCase();
    const muscles = [...ex.muscles_primary, ...ex.muscles_secondary].map(m => m.toLowerCase());

    if (cat === "legs") {
        return (
            pattern.includes("squat") ||
            pattern.includes("lunge") ||
            muscles.some(m =>
                m.includes("quad") ||
                m.includes("glute") ||
                m.includes("hamstring") ||
                m.includes("calf")
            )
        );
    }

    if (cat === "core") {
        return (
            pattern.includes("core") ||
            pattern.includes("abs") ||
            muscles.some(m => m.includes("abs") || m.includes("oblique"))
        );
    }

    if (cat === "mobility") {
        return pattern.includes("mobility") || pattern.includes("stretch");
    }

    return pattern.includes(cat) || muscles.some(m => m.includes(cat));
}

function getFilteredExercises() {
    const q = state.search.trim().toLowerCase();
    return state.exercises.filter(ex => {
        const name = ex.name.toLowerCase();
        return (!q || name.includes(q)) && matchesCategory(ex);
    });
}

function renderEmpty(msg) {
    const list = getList();
    if (!list) return;
    list.innerHTML = `<div class="db-session-empty">${msg}</div>`;
}

function renderExercises() {
    const list = getList();
    if (!list) return;

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

    items.forEach(ex => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "db-session-item";
        btn.dataset.exerciseId = ex.databaseId;

        const name = document.createElement("div");
        name.className = "db-session-item-name";
        name.textContent = ex.name;

        btn.appendChild(name);

        btn.addEventListener("click", () => {
            if (!state.callback) return;

            state.callback({
                databaseId: ex.databaseId,
                id: ex.databaseId,
                name: ex.name,
                movement_pattern: ex.movement_pattern,
                muscles_primary: ex.muscles_primary,
                muscles_secondary: ex.muscles_secondary,
                equipment: ex.equipment,
                sets: 3,
                reps: "10",
                weight: 0,
                completed: false
            });

            closeModal();
        });

        fragment.appendChild(btn);
    });

    list.appendChild(fragment);
}

function extractExercises(data) {
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.exercises)) return data.exercises;
    if (Array.isArray(data)) return data;
    return [];
}

async function loadExercises() {
    state.loading = true;
    renderExercises();

    try {
        const data = await TrainingAPI.getExercises();
        const raw = extractExercises(data);

        state.exercises = raw
            .map(normalizeExercise)
            .filter(ex => ex.databaseId !== null && ex.name !== "Без назви");

        console.log("Dashboard exercises loaded:", state.exercises.length);
    } catch (err) {
        console.error("Failed to load dashboard exercises:", err);
        state.exercises = [];
        renderEmpty("Не вдалося завантажити вправи.");
    } finally {
        state.loading = false;
        renderExercises();
    }
}

export function openExerciseModal(callback) {
    state.callback = typeof callback === "function" ? callback : null;
    openModal();
    loadExercises();
}

export function closeExerciseModal() {
    closeModal();
}

export function initExerciseModal() {
    const modal = getModal();
    if (!modal) return;

    const search = document.getElementById("db-exercise-search");
    const filters = modal.querySelectorAll("[data-exercise-category]");

    if (search) {
        search.addEventListener("input", () => {
            state.search = search.value;
            renderExercises();
        });
    }

    filters.forEach(btn => {
        btn.addEventListener("click", () => {
            state.category = btn.dataset.exerciseCategory || "all";
            filters.forEach(f => f.classList.remove("active"));
            btn.classList.add("active");
            renderExercises();
        });
    });

    modal.querySelectorAll("[data-close-exercise-modal]").forEach(btn => {
        btn.addEventListener("click", closeModal);
    });

    modal.addEventListener("click", e => {
        if (e.target === modal) closeModal();
    });
}
