import { ICONS } from "../../../icons/index.js";

type NumberChangeHandler =
    (value: number) => void;

type RepsChangeHandler =
    (value: string) => void;

export function createCounterField(
    label: string,
    iconSvg: string,
    value: number,
    onChange: NumberChangeHandler
): HTMLDivElement {
    const field =
        document.createElement("div");

    field.className =
        "tr-plan-field";

    field.innerHTML = `
        <div class="tr-plan-field-label-row">
            <span class="tr-plan-field-icon">${iconSvg}</span>
            <span class="tr-plan-field-label">${label}</span>
        </div>

        <div class="tr-input-inline">
            <input
                type="number"
                class="tr-input-field tr-plan-counter-input"
                value="${value}"
                min="0"
            >

            <div class="tr-input-arrows">
                <div class="tr-arrow tr-arrow-up"></div>
                <div class="tr-arrow tr-arrow-down"></div>
            </div>

            <span class="tr-input-inline-label"></span>
        </div>
    `;

    const input =
        field.querySelector<HTMLInputElement>(
            ".tr-plan-counter-input"
        );

    const up =
        field.querySelector<HTMLElement>(
            ".tr-arrow-up"
        );

    const down =
        field.querySelector<HTMLElement>(
            ".tr-arrow-down"
        );

    if (!input || !up || !down) {
        return field;
    }

    up.onclick = () => {
        const current =
            Number(input.value) || 0;

        const next =
            current + 1;

        input.value =
            String(next);

        onChange(next);
    };

    down.onclick = () => {
        const current =
            Number(input.value) || 0;

        const next =
            Math.max(0, current - 1);

        input.value =
            String(next);

        onChange(next);
    };

    input.oninput = () => {
        const value =
            Number(input.value);

        if (!Number.isNaN(value)) {
            onChange(value);
        }
    };

    return field;
}

export function createRepsField(
    value: string | number,
    onChange: RepsChangeHandler
): HTMLDivElement {
    const field =
        document.createElement("div");

    field.className =
        "tr-plan-field";

    field.innerHTML = `
        <div class="tr-plan-field-label-row">
            <span class="tr-plan-field-icon">
                ${ICONS.exercise}
            </span>
            <span class="tr-plan-field-label">
                Повтори
            </span>
        </div>

        <div class="tr-input-inline">
            <input
                type="text"
                class="tr-input-field tr-plan-reps-input"
                value="${value}"
            >

            <div class="tr-input-arrows">
                <div class="tr-arrow tr-arrow-up"></div>
                <div class="tr-arrow tr-arrow-down"></div>
            </div>

            <span class="tr-input-inline-label"></span>
        </div>
    `;

    const input =
        field.querySelector<HTMLInputElement>(
            ".tr-plan-reps-input"
        );

    const up =
        field.querySelector<HTMLElement>(
            ".tr-arrow-up"
        );

    const down =
        field.querySelector<HTMLElement>(
            ".tr-arrow-down"
        );

    if (!input || !up || !down) {
        return field;
    }

    const parseRange = (
        value: string
    ): [number, number] => {
        const parts =
            value
                .split("-")
                .map(Number);

        if (
            parts.length !== 2 ||
            parts.some(
                number =>
                    Number.isNaN(number)
            )
        ) {
            return [8, 12];
        }

        return [
            parts[0],
            parts[1]
        ];
    };

    const updateRange = (
        first: number,
        second: number
    ): void => {
        const next =
            `${first}-${second}`;

        input.value =
            next;

        onChange(next);
    };

    up.onclick = () => {
        const [first, second] =
            parseRange(input.value);

        updateRange(
            first + 1,
            second + 1
        );
    };

    down.onclick = () => {
        let [first, second] =
            parseRange(input.value);

        first =
            Math.max(1, first - 1);

        second =
            Math.max(
                first,
                second - 1
            );

        updateRange(
            first,
            second
        );
    };

    input.oninput = () => {
        const [first, second] =
            parseRange(input.value);

        updateRange(
            first,
            second
        );
    };

    return field;
}