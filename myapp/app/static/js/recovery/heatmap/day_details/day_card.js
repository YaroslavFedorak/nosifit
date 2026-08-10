import { formatMiniBar, formatScore } from "../formatters.js";

export function createDayCard(title, score, extra) {
    const card = document.createElement("div");
    card.className = "rc-day-card";

    const header = document.createElement("div");
    header.className = "rc-day-card-title";
    header.textContent = title;

    const value = document.createElement("div");
    value.className = "rc-day-card-value";
    value.textContent = formatScore(score);

    const bar = document.createElement("div");
    bar.className = "rc-day-card-bar";
    bar.textContent = formatMiniBar(score);

    const extraInfo = document.createElement("div");
    extraInfo.className = "rc-day-card-extra";
    extraInfo.textContent = extra || "";

    card.appendChild(header);
    card.appendChild(value);
    card.appendChild(bar);
    card.appendChild(extraInfo);

    return card;
}
