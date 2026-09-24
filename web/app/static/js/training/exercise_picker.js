import { trainingStore } from "./store.js";
import { exercise_t, t } from "../i18n/index.js";
let pickerCallback = null;
function getExerciseName(exercise) {
    if (!exercise.slug) {
        return exercise.name;
    }
    const translated = exercise_t(exercise.slug);
    return translated ===
        `${exercise.slug}.name`
        ? exercise.name
        : translated;
}
export function openExercisePicker(callback) {
    pickerCallback = callback;
    const modal = document.getElementById("tr-modal-picker");
    if (!modal) {
        return;
    }
    modal.classList.add("open");
}
export function initExercisePicker() {
    const modal = document.getElementById("tr-modal-picker");
    const list = document.getElementById("tr-ex-list");
    const search = document.getElementById("tr-ex-search");
    const categories = document.querySelectorAll(".tr-ex-cat");
    if (!modal ||
        !list ||
        !search) {
        return;
    }
    const closeButtons = modal.querySelectorAll("[data-close-picker]");
    let currentCategory = "all";
    const renderList = (items) => {
        list.innerHTML = "";
        if (!items.length) {
            const empty = document.createElement("div");
            empty.className =
                "tr-ex-modal-empty";
            empty.textContent =
                t("recommendations.exercisesEmpty");
            list.appendChild(empty);
            return;
        }
        items.forEach(exercise => {
            const row = document.createElement("div");
            row.className =
                "tr-ex-modal-item";
            row.textContent =
                getExerciseName(exercise);
            row.onclick = () => {
                pickerCallback?.(exercise);
                modal.classList.remove("open");
            };
            list.appendChild(row);
        });
    };
    const filterItems = () => {
        const query = search.value
            .trim()
            .toLowerCase();
        let items = [...trainingStore.exercises];
        if (currentCategory !==
            "all") {
            items =
                items.filter(exercise => {
                    const muscles = exercise
                        .muscles_primary ||
                        [];
                    return muscles.some(muscle => muscle
                        .toLowerCase()
                        .includes(currentCategory));
                });
        }
        if (query) {
            items =
                items.filter(exercise => {
                    const localizedName = getExerciseName(exercise).toLowerCase();
                    const originalName = exercise.name
                        .toLowerCase();
                    return (localizedName.includes(query) ||
                        originalName.includes(query));
                });
        }
        renderList(items);
    };
    const closeModal = () => {
        modal.classList.remove("open");
        pickerCallback = null;
    };
    renderList(trainingStore.exercises);
    search.oninput =
        filterItems;
    categories.forEach(button => {
        button.onclick = () => {
            currentCategory =
                button.dataset.cat ||
                    "all";
            categories.forEach(category => category.classList.remove("active"));
            button.classList.add("active");
            filterItems();
        };
    });
    closeButtons.forEach(button => {
        button.onclick =
            closeModal;
    });
    modal.addEventListener("click", event => {
        if (event.target === modal) {
            closeModal();
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" &&
            modal.classList.contains("open")) {
            closeModal();
        }
    });
}
