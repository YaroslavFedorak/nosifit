import { trainingStore } from "./store.js";

import type {
    Exercise
} from "./api.js";

import {
    t
} from "../i18n/index.js";

type PickerCallback =
    (exercise: Exercise) => void;

let pickerCallback:
    PickerCallback | null = null;

export function openExercisePicker(
    callback: PickerCallback
): void {
    pickerCallback = callback;

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
                    t("recommendations.exercisesEmpty");

                list.appendChild(empty);

                return;
            }

            items.forEach(exercise => {
                const row =
                    document.createElement("div");

                row.className =
                    "tr-ex-modal-item";

                row.textContent =
                    exercise.name;

                row.onclick = () => {
                    pickerCallback?.(exercise);

                    modal.classList.remove(
                        "open"
                    );
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

                            return muscles.some(
                                muscle =>
                                    muscle
                                        .toLowerCase()
                                        .includes(
                                            currentCategory
                                        )
                            );
                        }
                    );
            }

            if (query) {
                items =
                    items.filter(
                        exercise =>
                            exercise.name
                                .toLowerCase()
                                .includes(query)
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
                modal.classList.contains("open")
            ) {
                closeModal();
            }
        }
    );
}