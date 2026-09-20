import { trainingStore } from "./store.js";
let pickerCallback = null;
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
        !search ||
        !categories.length) {
        return;
    }
    const closeButtons = modal.querySelectorAll("[data-close-picker]");
    const renderList = (items) => {
        list.innerHTML = "";
        items.forEach(exercise => {
            const row = document.createElement("div");
            row.className =
                "tr-ex-modal-item";
            row.textContent =
                exercise.name;
            row.onclick = () => {
                pickerCallback?.(exercise);
                modal.classList.remove("open");
            };
            list.appendChild(row);
        });
    };
    let currentCategory = "all";
    const filterItems = () => {
        const query = search.value
            .trim()
            .toLowerCase();
        let items = trainingStore.exercises;
        if (currentCategory !==
            "all") {
            items =
                items.filter(exercise => (exercise
                    .muscles_primary ||
                    [])
                    .map(muscle => muscle.toLowerCase())
                    .includes(currentCategory));
        }
        if (query) {
            items =
                items.filter(exercise => exercise.name
                    .toLowerCase()
                    .includes(query));
        }
        renderList(items);
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
        button.onclick = () => {
            modal.classList.remove("open");
        };
    });
}
