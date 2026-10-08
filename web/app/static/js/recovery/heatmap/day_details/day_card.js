export function createMiniCard(name, value, status, barFill = 0) {
    const card = document.createElement("div");
    card.className =
        "rc-mini-card";
    const title = document.createElement("div");
    title.className =
        "rc-mini-title";
    title.textContent =
        name;
    const row = document.createElement("div");
    row.className =
        "rc-mini-row";
    const valueElement = document.createElement("div");
    valueElement.className =
        "rc-mini-value";
    valueElement.textContent =
        String(value);
    const statusElement = document.createElement("div");
    statusElement.className =
        "rc-mini-status";
    statusElement.textContent =
        status;
    row.appendChild(valueElement);
    row.appendChild(statusElement);
    const bar = document.createElement("div");
    bar.className =
        "rc-mini-bar";
    const fill = document.createElement("div");
    fill.className =
        "rc-mini-bar-fill";
    const numericFill = Number(barFill);
    const normalized = Number.isFinite(numericFill)
        ? Math.max(0, Math.min(100, numericFill))
        : 0;
    fill.style.width =
        `${normalized}%`;
    bar.appendChild(fill);
    card.appendChild(title);
    card.appendChild(row);
    card.appendChild(bar);
    return card;
}
