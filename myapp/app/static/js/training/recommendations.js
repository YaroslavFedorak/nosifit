import { ICONS } from "/static/js/icons/index.js";

const safeArr = v => Array.isArray(v) ? v : (v ? [v] : []);

const MUSCLE_NAMES = {
    spine: "Хребет",
    traps: "Трапеції",
    abs: "Прес",
    obliques: "Косі м’язи живота",
    "hip-flexors": "Згиначі стегна",
    chest: "Груди",
    back: "Спина",
    glutes: "Сідниці",
    quads: "Квадрицепси",
    shoulders: "Плечі",
    triceps: "Трицепс",
    core: "Кор",
    legs: "Ноги"
};

const capitalize = s => s.charAt(0).toUpperCase() + s.slice(1);

const translateMuscle = m => {
    const key = String(m).toLowerCase();
    return MUSCLE_NAMES[key] || capitalize(m);
};

export function renderRecommendations(data) {
    renderWeakPoints(data.muscles || {});
    renderRecommendedExercises(data.recommended_exercises || []);
    renderBalance(data.muscles || {});
}

function renderWeakPoints(muscles) {
    const box = document.getElementById("tr-weak-points");
    if (!box) return;

    const items = safeArr(muscles.weak).slice(0, 6);

    box.innerHTML = items
        .map(m => `<div class="tr-weak-item">${translateMuscle(m)}</div>`)
        .join("");
}

function renderRecommendedExercises(list) {
    const box = document.getElementById("tr-rec-grid");
    if (!box) return;

    const items = safeArr(list).slice(0, 3);

    box.innerHTML = items
        .map(item => {
            const reason = safeArr(item.reasons)[0] || "";
            const reasonText = capitalize(reason);
            return `
                <div class="tr-rec-line-item">
                    <div class="tr-rec-line-item-top">
                        ${ICONS.exercise}
                        <span>${item.exercise}</span>
                    </div>
                    <div class="tr-rec-item-tag">${reasonText}</div>
                </div>
            `;
        })
        .join("");
}

function renderBalance(muscles) {
    const balancedBox = document.getElementById("tr-balance-balanced");
    const overloadedBox = document.getElementById("tr-balance-overloaded");

    if (!balancedBox || !overloadedBox) return;

    balancedBox.innerHTML = safeArr(muscles.balanced)
        .slice(0, 3)
        .map(
            m =>
                `<div class="tr-balance-item tr-balance-item-balanced">${ICONS.balanced}<span>${translateMuscle(
                    m
                )}</span></div>`
        )
        .join("");

    overloadedBox.innerHTML = safeArr(muscles.overloaded)
        .slice(0, 3)
        .map(
            m =>
                `<div class="tr-balance-item tr-balance-item-overloaded">${ICONS.overloaded}<span>${translateMuscle(
                    m
                )}</span></div>`
        )
        .join("");
}
