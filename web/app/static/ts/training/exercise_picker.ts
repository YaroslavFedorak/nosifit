import { trainingStore } from "./store.js";

import {
    MUSCLE_CATEGORIES
} from "./measurement.js";

import type {
Exercise
} from "./api.js";

import {
exercise_t,
t
} from "../i18n/index.js";

type PickerCallback =
(exercise: Exercise) => void;

// allowed: equipment of the day being planned (null = no limit). Exercises
// that need anything else are shown but cannot be picked.
export type PickerOptions = {
    allowed?: Set<string> | null;
};

let pickerCallback:
PickerCallback | null = null;

let pickerOptions:
PickerOptions = {};

function getExerciseName(
exercise: Exercise
): string {
if (!exercise.slug) {
return exercise.name;
}

const translated =
    exercise_t(exercise.slug);

return translated ===
    `${exercise.slug}.name`
    ? exercise.name
    : translated;

}

export function openExercisePicker(
callback: PickerCallback,
options: PickerOptions = {}
): void {
pickerCallback = callback;

pickerOptions = options;

const modal =
    document.getElementById(
        "tr-modal-picker"
    );

if (!modal) {
    return;
}

modal.classList.add("open");

}

export function initExercisePicker(): void {
const modal =
document.getElementById(
"tr-modal-picker"
);

const list =
    document.getElementById(
        "tr-ex-list"
    );

const search =
    document.getElementById(
        "tr-ex-search"
    ) as HTMLInputElement | null;

const categories =
    document.querySelectorAll<HTMLElement>(
        ".tr-ex-cat"
    );

if (
    !modal ||
    !list ||
    !search
) {
    return;
}

const closeButtons =
    modal.querySelectorAll<HTMLElement>(
        "[data-close-picker]"
    );

let currentCategory = "all";

const renderList =
    (items: Exercise[]): void => {
        list.innerHTML = "";

        if (!items.length) {
            const empty =
                document.createElement("div");

            empty.className =
                "tr-ex-modal-empty";

            empty.textContent =
                t(
                    "recommendations.exercisesEmpty"
                );

            list.appendChild(empty);

            return;
        }

        items.forEach(exercise => {
            const row =
                document.createElement("div");

            row.className =
                "tr-ex-modal-item";

            const needed =
                (exercise.equipment ?? []).filter(
                    slug =>
                        slug !== "bodyweight"
                );

            const allowed =
                pickerOptions.allowed ?? null;

            const unavailable =
                allowed !== null &&
                needed.some(
                    slug =>
                        !allowed.has(slug)
                );

            const name =
                document.createElement("span");

            name.textContent =
                getExerciseName(
                    exercise
                );

            row.appendChild(name);

            if (needed.length) {
                const meta =
                    document.createElement("small");

                meta.className =
                    "tr-ex-modal-equipment";

                meta.textContent =
                    needed
                        .map(
                            slug =>
                                t(
                                    `plan.equipmentNames.${slug}`
                                )
                        )
                        .join(", ");

                row.appendChild(meta);
            }

            if (unavailable) {
                row.classList.add(
                    "unavailable"
                );

                row.setAttribute(
                    "aria-disabled",
                    "true"
                );

                row.title =
                    t("plan.unavailable");

                list.appendChild(row);

                return;
            }

            row.tabIndex = 0;

            row.setAttribute(
                "role",
                "button"
            );

            const choose = (): void => {
                pickerCallback?.(
                    exercise
                );

                modal.classList.remove(
                    "open"
                );
            };

            row.onclick = choose;

            row.onkeydown = event => {
                if (
                    event.key === "Enter" ||
                    event.key === " "
                ) {
                    event.preventDefault();

                    choose();
                }
            };

            list.appendChild(row);
        });
    };

const filterItems =
    (): void => {
        const query =
            search.value
                .trim()
                .toLowerCase();

        let items =
            [...trainingStore.exercises];

        if (
            currentCategory !==
            "all"
        ) {
            items =
                items.filter(
                    exercise => {
                        const muscles =
                            exercise
                                .muscles_primary ||
                            [];

                        const categoryMuscles =
                            MUSCLE_CATEGORIES[
                                currentCategory
                            ] ?? [currentCategory];

                        return muscles.some(
                            muscle =>
                                categoryMuscles.includes(
                                    muscle.toLowerCase()
                                )
                        );
                    }
                );
        }

        if (query) {
            items =
                items.filter(
                    exercise => {
                        const localizedName =
                            getExerciseName(
                                exercise
                            ).toLowerCase();

                        const originalName =
                            exercise.name
                                .toLowerCase();

                        return (
                            localizedName.includes(
                                query
                            ) ||
                            originalName.includes(
                                query
                            )
                        );
                    }
                );
        }

        renderList(items);
    };

const closeModal =
    (): void => {
        modal.classList.remove(
            "open"
        );

        pickerCallback = null;
    };

renderList(
    trainingStore.exercises
);

search.oninput =
    filterItems;

categories.forEach(button => {
    button.onclick = () => {
        currentCategory =
            button.dataset.cat ||
            "all";

        categories.forEach(
            category =>
                category.classList.remove(
                    "active"
                )
        );

        button.classList.add(
            "active"
        );

        filterItems();
    };
});

closeButtons.forEach(button => {
    button.onclick =
        closeModal;
});

modal.addEventListener(
    "click",
    event => {
        if (
            event.target === modal
        ) {
            closeModal();
        }
    }
);

document.addEventListener(
    "keydown",
    event => {
        if (
            event.key === "Escape" &&
            modal.classList.contains(
                "open"
            )
        ) {
            closeModal();
        }
    }
);

}
