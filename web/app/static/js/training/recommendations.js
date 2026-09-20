import { ICONS } from "../icons/index.js";
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
const REASON_NAMES = {
    "improves weak muscle group": "Розвиває слабку групу",
    "improves weak movement pattern": "Покращує слабкий рух",
    "helps reverse regression": "Допомагає відновити прогрес",
    "helps break plateau": "Допомагає подолати плато",
    "supports an undertrained muscle": "Підсилює недостатньо треновану групу",
    "adds exercise variety": "Додає різноманітність",
    "targets your weak point": "Працює над слабким місцем",
    progression: "Підтримує прогрес",
    "low frequency": "Група тренується недостатньо часто",
    "high frequency": "Враховано високу частоту навантаження"
};
function safeArray(value) {
    if (Array.isArray(value)) {
        return value;
    }
    if (value === null || value === undefined) {
        return [];
    }
    return [value];
}
function capitalize(value) {
    const text = String(value || "").trim();
    if (!text) {
        return "";
    }
    return text.charAt(0).toUpperCase() + text.slice(1);
}
function translateMuscle(value) {
    const key = String(value || "")
        .trim()
        .toLowerCase();
    return MUSCLE_NAMES[key] || capitalize(value);
}
function translateReason(value) {
    const key = String(value || "")
        .trim()
        .toLowerCase();
    return REASON_NAMES[key] || capitalize(value);
}
export function renderRecommendations(data) {
    const muscles = data?.muscles || {};
    const recommendations = safeArray(data?.recommended_exercises);
    renderWeakPoints(muscles);
    renderRecommendedExercises(recommendations);
    renderBalance(muscles);
}
function renderWeakPoints(muscles) {
    const box = document.getElementById("tr-weak-points");
    if (!box) {
        return;
    }
    const items = safeArray(muscles.weak)
        .filter(Boolean)
        .slice(0, 4);
    if (items.length === 0) {
        box.innerHTML = `
            <div class="tr-rec-empty">
                <strong>Недостатньо даних для визначення слабких груп</strong>
                <span>Додайте кілька тренувань, щоб отримати персональний аналіз</span>
            </div>
        `;
        return;
    }
    box.innerHTML = items
        .map(muscle => `
                <div class="tr-weak-item">
                    ${translateMuscle(muscle)}
                </div>
            `)
        .join("");
}
function renderRecommendedExercises(list) {
    const box = document.getElementById("tr-rec-grid");
    if (!box) {
        return;
    }
    const items = list
        .filter(item => item &&
        typeof item.exercise === "string" &&
        item.exercise.trim().length > 0)
        .slice(0, 3);
    if (items.length === 0) {
        box.innerHTML = `
            <div class="tr-rec-empty">
                <strong>Поки немає персональних рекомендацій</strong>
                <span>Додайте кілька тренувань, щоб система могла проаналізувати ваш прогрес</span>
            </div>
        `;
        return;
    }
    box.innerHTML = items
        .map(item => {
        const reasons = safeArray(item.reasons)
            .filter(Boolean)
            .slice(0, 2);
        return `
                <div class="tr-rec-line-item">
                    <div class="tr-rec-line-item-top">
                        ${ICONS.exercise}
                        <span>${item.exercise || ""}</span>
                    </div>

                    ${reasons.length > 0
            ? reasons
                .map(reason => `
                                        <div class="tr-rec-item-tag">
                                            ${translateReason(reason)}
                                        </div>
                                    `)
                .join("")
            : ""}
                </div>
            `;
    })
        .join("");
}
function renderBalance(muscles) {
    const balancedBox = document.getElementById("tr-balance-balanced");
    const overloadedBox = document.getElementById("tr-balance-overloaded");
    if (!balancedBox || !overloadedBox) {
        return;
    }
    const balanced = safeArray(muscles.balanced)
        .filter(Boolean)
        .slice(0, 3);
    const overloaded = safeArray(muscles.overloaded)
        .filter(Boolean)
        .slice(0, 3);
    if (balanced.length === 0 &&
        overloaded.length === 0) {
        balancedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <strong>Недостатньо даних для аналізу балансу</strong>
                <span>Продовжуйте тренуватися, щоб отримати аналіз м’язових груп</span>
            </div>
        `;
        overloadedBox.innerHTML = "";
        return;
    }
    if (balanced.length === 0) {
        balancedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <span>Немає груп у збалансованому діапазоні</span>
            </div>
        `;
    }
    else {
        balancedBox.innerHTML = balanced
            .map(muscle => `
                    <div class="tr-balance-item tr-balance-item-balanced">
                        ${ICONS.balanced}
                        <span>${translateMuscle(muscle)}</span>
                    </div>
                `)
            .join("");
    }
    if (overloaded.length === 0) {
        overloadedBox.innerHTML = `
            <div class="tr-rec-empty tr-balance-empty">
                <span>Немає перевантажених груп</span>
            </div>
        `;
    }
    else {
        overloadedBox.innerHTML = overloaded
            .map(muscle => `
                    <div class="tr-balance-item tr-balance-item-overloaded">
                        ${ICONS.overloaded}
                        <span>${translateMuscle(muscle)}</span>
                    </div>
                `)
            .join("");
    }
}
