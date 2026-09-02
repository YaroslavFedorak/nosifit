/**
 * Remove all children from an element.
 * @param {HTMLElement} el
 */
export function clearElement(el) {
    while (el.firstChild) {
        el.removeChild(el.firstChild);
    }
}

/**
 * Create a card container.
 * @param {string} className
 * @returns {HTMLElement}
 */
export function createCard(className) {
    const card = document.createElement("div");
    card.className = className;
    return card;
}

/**
 * Create a title element.
 * @param {string} text
 * @returns {HTMLElement}
 */
export function createTitle(text) {
    const h3 = document.createElement("h3");
    h3.textContent = text;
    return h3;
}

/**
 * Create a label-value row.
 * @param {string} label
 * @param {string|number} value
 * @returns {HTMLElement}
 */
export function createLabelValue(label, value) {
    const row = document.createElement("div");
    const spanLabel = document.createElement("span");
    const spanValue = document.createElement("strong");

    spanLabel.textContent = `${label}: `;
    spanValue.textContent = value;

    row.appendChild(spanLabel);
    row.appendChild(spanValue);
    return row;
}

/**
 * Create a loading placeholder.
 * @param {string} text
 * @returns {HTMLElement}
 */
export function createLoading(text) {
    const div = document.createElement("div");
    div.className = "loading";
    div.textContent = text;
    return div;
}

/**
 * Create an error placeholder.
 * @param {string} text
 * @returns {HTMLElement}
 */
export function createError(text) {
    const div = document.createElement("div");
    div.className = "error";
    div.textContent = text;
    return div;
}

/**
 * Create an empty placeholder.
 * @param {string} text
 * @returns {HTMLElement}
 */
export function createEmpty(text) {
    const div = document.createElement("div");
    div.className = "empty";
    div.textContent = text;
    return div;
}
