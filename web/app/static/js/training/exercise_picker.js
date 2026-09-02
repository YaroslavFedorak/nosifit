import { trainingStore } from "./store.js";

let pickerCallback = null;

export function openExercisePicker(callback) {
    pickerCallback = callback;
    const modal = document.getElementById("tr-modal-picker");
    if (!modal) return;
    modal.classList.add("open");
}

export function initExercisePicker() {
    const modal = document.getElementById("tr-modal-picker");
    const list = document.getElementById("tr-ex-list");
    const search = document.getElementById("tr-ex-search");
    const cats = document.querySelectorAll(".tr-ex-cat");

    if (!modal || !list || !search || !cats.length) return;

    const closeBtns = modal.querySelectorAll("[data-close-picker]");

    const renderList = items => {
        list.innerHTML = "";
        items.forEach(ex => {
            const row = document.createElement("div");
            row.className = "tr-ex-modal-item";
            row.textContent = ex.name;
            row.onclick = () => {
                if (pickerCallback) pickerCallback(ex);
                modal.classList.remove("open");
            };
            list.appendChild(row);
        });
    };

    let currentCat = "all";

    const filterItems = () => {
        const q = search.value.trim().toLowerCase();
        let items = trainingStore.exercises || [];

        if (currentCat !== "all") {
            items = items.filter(ex =>
                (ex.muscles_primary || [])
                    .map(m => m.toLowerCase())
                    .includes(currentCat)
            );
        }

        if (q) {
            items = items.filter(ex =>
                ex.name.toLowerCase().includes(q)
            );
        }

        renderList(items);
    };

    renderList(trainingStore.exercises || []);

    search.oninput = filterItems;

    cats.forEach(btn => {
        btn.onclick = () => {
            currentCat = btn.dataset.cat;
            cats.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            filterItems();
        };
    });

    closeBtns.forEach(btn => {
        btn.onclick = () => modal.classList.remove("open");
    });
}
