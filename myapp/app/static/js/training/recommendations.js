import { ICONS } from "/static/js/icons/index.js";

const safeArr = value =>
    Array.isArray(value)
        ? value
        : value
          ? [value]
          : [];

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
    biceps: "Біцепс",
    core: "Кор",
    legs: "Ноги",
    "lower-back": "Поперек"
};

const capitalize = value => {
    const text = String(value || "");

    return text
        ? text.charAt(0).toUpperCase() + text.slice(1)
        : "";
};

const translateMuscle = muscle => {
    const key = String(muscle || "").toLowerCase();

    return MUSCLE_NAMES[key] || capitalize(key);
};

const translateReason = reason => {
    const map = {
        "improves weak muscle group": "Розвиває слабку групу",
        "improves weak movement pattern": "Покращує слабкий рух",
        "helps reverse regression": "Допомагає відновити прогрес",
        "helps break plateau": "Допомагає подолати плато",
        "supports an undertrained muscle": "Підсилює недостатньо треновану групу",
        "adds exercise variety": "Додає різноманітність"
    };

    return map[String(reason || "").toLowerCase()]
        || capitalize(reason);
};

export function renderRecommendations(data) {
    const muscles = data?.muscles || {};
    const recommendations = safeArr(
        data?.recommended_exercises
    );

    renderWeakPoints(muscles);
    renderRecommendedExercises(recommendations);
    renderBalance(muscles);
}

function renderWeakPoints(muscles) {
    const box = document.getElementById("tr-weak-points");

    if (!box) return;

    const items = safeArr(muscles.weak)
        .slice(0, 6);

    box.innerHTML = items
        .map(
            muscle =>
                `<div class="tr-weak-item">${translateMuscle(
                    muscle
                )}</div>`
        )
        .join("");
}

function renderRecommendedExercises(list) {
    const box = document.getElementById("tr-rec-grid");

    if (!box) return;

    const items = list.slice(0, 3);

    if (items.length === 0) {
        box.innerHTML = `
            <div class="tr-rec-empty">
                Недостатньо даних для персональних рекомендацій
            </div>
        `;
        return;
    }

    box.innerHTML = items
        .map(item => {
            const reasons = safeArr(item?.reasons)
                .filter(Boolean)
                .slice(0, 2);

            return `
                <div class="tr-rec-line-item">
                    <div class="tr-rec-line-item-top">
                        ${ICONS.exercise}
                        <span>${item?.exercise || ""}</span>
                    </div>

                    ${
                        reasons.length
                            ? reasons
                                  .map(
                                      reason => `
                                        <div class="tr-rec-item-tag">
                                            ${translateReason(reason)}
                                        </div>
                                    `
                                  )
                                  .join("")
                            : ""
                    }
                </div>
            `;
        })
        .join("");
}

function renderBalance(muscles) {
    const balancedBox = document.getElementById(
        "tr-balance-balanced"
    );

    const overloadedBox = document.getElementById(
        "tr-balance-overloaded"
    );

    if (!balancedBox || !overloadedBox) return;

    const balanced = safeArr(
        muscles.balanced
    ).slice(0, 3);

    const overloaded = safeArr(
        muscles.overloaded
    ).slice(0, 3);

    balancedBox.innerHTML = balanced
        .map(
            muscle =>
                `
                <div class="tr-balance-item tr-balance-item-balanced">
                    ${ICONS.balanced}
                    <span>${translateMuscle(muscle)}</span>
                </div>
                `
        )
        .join("");

    overloadedBox.innerHTML = overloaded
        .map(
            muscle =>
                `
                <div class="tr-balance-item tr-balance-item-overloaded">
                    ${ICONS.overloaded}
                    <span>${translateMuscle(muscle)}</span>
                </div>
                `
        )
        .join("");
}