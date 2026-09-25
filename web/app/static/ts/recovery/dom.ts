export function clearElement(
    el: HTMLElement
): void {
    while (el.firstChild) {
        el.removeChild(el.firstChild);
    }
}

export function createCard(
    className: string
): HTMLDivElement {
    const card =
        document.createElement(
            "div"
        );

    card.className =
        className;

    return card;
}

export function createTitle(
    text: string
): HTMLHeadingElement {
    const h3 =
        document.createElement(
            "h3"
        );

    h3.textContent =
        text;

    return h3;
}

export function createLabelValue(
    label: string,
    value: string | number
): HTMLDivElement {
    const row =
        document.createElement(
            "div"
        );

    const spanLabel =
        document.createElement(
            "span"
        );

    const spanValue =
        document.createElement(
            "strong"
        );

    spanLabel.textContent =
        `${label}: `;

    spanValue.textContent =
        String(value);

    row.appendChild(
        spanLabel
    );

    row.appendChild(
        spanValue
    );

    return row;
}

export function createLoading(
    text: string
): HTMLDivElement {
    const div =
        document.createElement(
            "div"
        );

    div.className =
        "loading";

    div.textContent =
        text;

    return div;
}

export function createError(
    text: string
): HTMLDivElement {
    const div =
        document.createElement(
            "div"
        );

    div.className =
        "error";

    div.textContent =
        text;

    return div;
}

export function createEmpty(
    text: string
): HTMLDivElement {
    const div =
        document.createElement(
            "div"
        );

    div.className =
        "empty";

    div.textContent =
        text;

    return div;
}