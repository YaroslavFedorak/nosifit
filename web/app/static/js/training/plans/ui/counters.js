import { ICONS } from "../../../icons/index.js";

export function createCounterField(label, iconSvg, value, onChange) {
    const field = document.createElement("div");
    field.className = "tr-plan-field";

    field.innerHTML = `
        <div class="tr-plan-field-label-row">
            <span class="tr-plan-field-icon">${iconSvg}</span>
            <span class="tr-plan-field-label">${label}</span>
        </div>

        <div class="tr-input-inline">
            <input type="number" class="tr-input-field tr-plan-counter-input" value="${value}" min="0">

            <div class="tr-input-arrows">
                <div class="tr-arrow tr-arrow-up"></div>
                <div class="tr-arrow tr-arrow-down"></div>
            </div>

            <span class="tr-input-inline-label"></span>
        </div>
    `;

    const input = field.querySelector(".tr-plan-counter-input");
    const up = field.querySelector(".tr-arrow-up");
    const down = field.querySelector(".tr-arrow-down");

    up.onclick = () => {
        const val = Number(input.value);
        const next = val + 1;
        input.value = next;
        onChange(next);
    };

    down.onclick = () => {
        const val = Number(input.value);
        const next = Math.max(0, val - 1);
        input.value = next;
        onChange(next);
    };

    input.oninput = () => {
        const val = Number(input.value);
        if (!Number.isNaN(val)) onChange(val);
    };

    return field;
}

export function createRepsField(value, onChange) {
    const field = document.createElement("div");
    field.className = "tr-plan-field";

    field.innerHTML = `
        <div class="tr-plan-field-label-row">
            <span class="tr-plan-field-icon">${ICONS.exercise}</span>
            <span class="tr-plan-field-label">Повтори</span>
        </div>

        <div class="tr-input-inline">
            <input type="text" class="tr-input-field tr-plan-reps-input" value="${value}">

            <div class="tr-input-arrows">
                <div class="tr-arrow tr-arrow-up"></div>
                <div class="tr-arrow tr-arrow-down"></div>
            </div>

            <span class="tr-input-inline-label"></span>
        </div>
    `;

    const input = field.querySelector(".tr-plan-reps-input");
    const up = field.querySelector(".tr-arrow-up");
    const down = field.querySelector(".tr-arrow-down");

    function parseRange(val) {
        const parts = val.split("-").map(Number);
        if (parts.length !== 2 || parts.some(n => Number.isNaN(n))) {
            return [8, 12];
        }
        return parts;
    }

    function updateRange(a, b) {
        const next = `${a}-${b}`;
        input.value = next;
        onChange(next);
    }

    up.onclick = () => {
        let [a, b] = parseRange(input.value);
        a += 1;
        b += 1;
        updateRange(a, b);
    };

    down.onclick = () => {
        let [a, b] = parseRange(input.value);
        a = Math.max(1, a - 1);
        b = Math.max(a, b - 1);
        updateRange(a, b);
    };

    input.oninput = () => {
        const [a, b] = parseRange(input.value);
        updateRange(a, b);
    };

    return field;
}
