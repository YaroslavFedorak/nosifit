import {
    TrainingAPI
} from "../widgets/training/api.js";

import {
    dashboard_t,
    exercise_t
} from "../../i18n/index.js";

interface ExerciseState {
    exercises: NormalizedExercise[];
    category: string;
    search: string;
    callback:
        | ((exercise: any) => void)
        | null;
    loading: boolean;
}

interface NormalizedExercise {
    id: string;
    databaseId: string | null;
    slug: string;
    name: string;
    originalName: string;
    movement_pattern: string;
    muscles_primary: string[];
    muscles_secondary: string[];
    equipment: string[];
    original: any;
}

const state: ExerciseState = {
    exercises: [],
    category: "all",
    search: "",
    callback: null,
    loading: false
};

function getModal():
    HTMLElement | null {
    return document.getElementById(
        "db-exercise-modal"
    );
}

function getList():
    HTMLElement | null {
    return document.getElementById(
        "db-exercise-list"
    );
}

function createLocalId(): string {
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

function normalizeDatabaseId(
    value: any
): string | null {
    return value
        ? String(value)
        : null;
}

function findExerciseId(
    exercise: any
): string | null {
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
        const id =
            normalizeDatabaseId(
                candidate
            );

        if (id !== null) {
            return id;
        }
    }

    return null;
}

function findExerciseSlug(
    exercise: any
): string {
    return String(
        exercise?.slug ??
        exercise?.exercise_slug ??
        exercise?.exerciseSlug ??
        exercise?.exercise?.slug ??
        exercise?.data?.slug ??
        ""
    ).trim();
}

function normalizeArray(
    value: any
): string[] {
    if (Array.isArray(value)) {
        return value;
    }

    if (
        typeof value === "string" &&
        value.trim()
    ) {
        return value
            .split(",")
            .map(
                item =>
                    item.trim()
            )
            .filter(Boolean);
    }

    return [];
}

function getTranslatedName(
    slug: string,
    fallback: string
): string {
    if (!slug) {
        return fallback;
    }

    const translated =
        exercise_t(slug);

    return translated !==
        `${slug}.name`
        ? translated
        : fallback;
}

function normalizeExercise(
    exercise: any
): NormalizedExercise {
    const originalName =
        String(
            exercise?.name ??
            exercise?.exercise_name ??
            exercise?.title ??
            exercise?.exercise?.name ??
            "Без назви"
        );

    const slug =
        findExerciseSlug(
            exercise
        );

    return {
        id: createLocalId(),

        databaseId:
            findExerciseId(
                exercise
            ),

        slug,

        name:
            getTranslatedName(
                slug,
                originalName
            ),

        originalName,

        movement_pattern:
            exercise?.movement_pattern ??
            exercise?.movementPattern ??
            exercise?.exercise
                ?.movement_pattern ??
            exercise?.exercise
                ?.movementPattern ??
            "",

        muscles_primary:
            normalizeArray(
                exercise?.muscles_primary ??
                exercise?.primary_muscles ??
                exercise?.exercise
                    ?.muscles_primary ??
                exercise?.exercise
                    ?.primary_muscles
            ),

        muscles_secondary:
            normalizeArray(
                exercise?.muscles_secondary ??
                exercise?.secondary_muscles ??
                exercise?.exercise
                    ?.muscles_secondary ??
                exercise?.exercise
                    ?.secondary_muscles
            ),

        equipment:
            normalizeArray(
                exercise?.equipment ??
                exercise?.exercise?.equipment
            ),

        original: exercise
    };
}

function openModal(): void {
    const modal = getModal();

    if (!modal) {
        return;
    }

    modal.classList.add("open");

    modal.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.classList.add(
        "db-modal-open"
    );
}

function closeModal(): void {
    const modal = getModal();

    if (!modal) {
        return;
    }

    modal.classList.remove("open");

    modal.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.classList.remove(
        "db-modal-open"
    );

    state.callback = null;
}

function matchesCategory(
    exercise: NormalizedExercise
): boolean {
    if (
        state.category === "all"
    ) {
        return true;
    }

    const category =
        state.category.toLowerCase();

    const pattern =
        (
            exercise.movement_pattern ||
            ""
        ).toLowerCase();

    const muscles = [
        ...exercise.muscles_primary,
        ...exercise.muscles_secondary
    ].map(
        muscle =>
            muscle.toLowerCase()
    );

    if (category === "legs") {
        return (
            pattern.includes("squat") ||
            pattern.includes("lunge") ||
            muscles.some(
                muscle =>
                    muscle.includes("quad") ||
                    muscle.includes("glute") ||
                    muscle.includes("hamstring") ||
                    muscle.includes("calf")
            )
        );
    }

    if (category === "core") {
        return (
            pattern.includes("core") ||
            pattern.includes("abs") ||
            muscles.some(
                muscle =>
                    muscle.includes("abs") ||
                    muscle.includes("oblique")
            )
        );
    }

    if (category === "mobility") {
        return (
            pattern.includes("mobility") ||
            pattern.includes("stretch")
        );
    }

    return (
        pattern.includes(category) ||
        muscles.some(
            muscle =>
                muscle.includes(category)
        )
    );
}

function getFilteredExercises():
    NormalizedExercise[] {
    const query =
        state.search
            .trim()
            .toLowerCase();

    return state.exercises.filter(
        exercise => {
            const name =
                exercise.name.toLowerCase();

            const originalName =
                exercise.originalName
                    .toLowerCase();

            const slug =
                exercise.slug
                    .toLowerCase();

            const matchesSearch =
                !query ||
                name.includes(query) ||
                originalName.includes(query) ||
                slug.includes(query);

            return (
                matchesSearch &&
                matchesCategory(
                    exercise
                )
            );
        }
    );
}

function renderEmpty(
    message: string
): void {
    const list = getList();

    if (!list) {
        return;
    }

    list.innerHTML =
        `<div class="db-session-empty">${message}</div>`;
}

function renderExercises(): void {
    const list = getList();

    if (!list) {
        return;
    }

    list.innerHTML = "";

    if (state.loading) {
        renderEmpty(
            dashboard_t(
                "exerciseModal.loading"
            )
        );

        return;
    }

    const items =
        getFilteredExercises();

    if (!items.length) {
        renderEmpty(
            dashboard_t(
                "exerciseModal.empty"
            )
        );

        return;
    }

    const fragment =
        document.createDocumentFragment();

    items.forEach(
        exercise => {
            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";

            button.className =
                "db-session-item";

            if (
                exercise.databaseId
            ) {
                button.dataset.exerciseId =
                    exercise.databaseId;
            }

            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "db-session-item-name";

            name.textContent =
                exercise.name;

            button.appendChild(
                name
            );

            button.addEventListener(
                "click",
                () => {
                    if (
                        !state.callback
                    ) {
                        return;
                    }

                    state.callback({
                        databaseId:
                            exercise.databaseId,

                        id:
                            exercise.databaseId,

                        slug:
                            exercise.slug,

                        name:
                            exercise.originalName,

                        movement_pattern:
                            exercise.movement_pattern,

                        muscles_primary:
                            exercise.muscles_primary,

                        muscles_secondary:
                            exercise.muscles_secondary,

                        equipment:
                            exercise.equipment,

                        sets: 3,

                        reps: "10",

                        weight: 0,

                        completed: false
                    });

                    closeModal();
                }
            );

            fragment.appendChild(
                button
            );
        }
    );

    list.appendChild(
        fragment
    );
}

function extractExercises(
    data: any
): any[] {
    if (
        Array.isArray(
            data?.items
        )
    ) {
        return data.items;
    }

    if (
        Array.isArray(
            data?.exercises
        )
    ) {
        return data.exercises;
    }

    if (Array.isArray(data)) {
        return data;
    }

    return [];
}

async function loadExercises():
    Promise<void> {
    state.loading = true;

    renderExercises();

    try {
        const data =
            await TrainingAPI.getExercises();

        const raw =
            extractExercises(
                data
            );

        state.exercises =
            raw
                .map(
                    normalizeExercise
                )
                .filter(
                    exercise =>
                        exercise.databaseId !==
                            null &&
                        exercise.originalName !==
                            "Без назви"
                );

        console.log(
            "Dashboard exercises loaded:",
            state.exercises.length
        );
    } catch (error) {
        console.error(
            "Failed to load dashboard exercises:",
            error
        );

        state.exercises = [];

        renderEmpty(
            dashboard_t(
                "exerciseModal.loadError"
            )
        );
    } finally {
        state.loading = false;

        renderExercises();
    }
}

export function openExerciseModal(
    callback:
        | ((exercise: any) => void)
        | null
): void {
    state.callback =
        typeof callback === "function"
            ? callback
            : null;

    openModal();

    void loadExercises();
}

export function closeExerciseModal():
    void {
    closeModal();
}

export function initExerciseModal():
    void {
    const modal = getModal();

    if (!modal) {
        return;
    }

    const search =
        document.getElementById(
            "db-exercise-search"
        ) as HTMLInputElement | null;

    const filters =
        modal.querySelectorAll<HTMLElement>(
            "[data-exercise-category]"
        );

    if (search) {
        search.addEventListener(
            "input",
            () => {
                state.search =
                    search.value;

                renderExercises();
            }
        );
    }

    filters.forEach(
        button => {
            button.addEventListener(
                "click",
                () => {
                    state.category =
                        button.dataset
                            .exerciseCategory ||
                        "all";

                    filters.forEach(
                        filter =>
                            filter.classList.remove(
                                "active"
                            )
                    );

                    button.classList.add(
                        "active"
                    );

                    renderExercises();
                }
            );
        }
    );

    modal
        .querySelectorAll<HTMLElement>(
            "[data-close-exercise-modal]"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    closeModal
                );
            }
        );

    modal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                modal
            ) {
                closeModal();
            }
        }
    );
}