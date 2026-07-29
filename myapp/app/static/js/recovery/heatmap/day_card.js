import { getLevel, formatMiniBar, formatScore } from "./formatters.js";

export function createDayCard(config) {
    const { kind, label, score, extra, icon } = config;
    const level = getLevel(score);

    const wrapper = document.createElement("div");
    wrapper.className = `rc-day-card rc-day-card-${kind}`;

    const header = document.createElement("div");
    header.className = "rc-day-card-header";

    const iconBox = document.createElement("span");
    iconBox.className = "rc-day-card-icon";
    if (icon) iconBox.innerHTML = icon;

    const title = document.createElement("span");
    title.className = "rc-day-card-title";
    title.textContent = label;

    header.appendChild(iconBox);
    header.appendChild(title);

    const main = document.createElement("div");
    main.className = "rc-day-card-main";

    const bar = document.createElement("span");
    bar.className = `rc-day-card-bar ${level}`;
    bar.textContent = formatMiniBar(score);

    const value = document.createElement("span");
    value.className = "rc-day-card-value";
    value.textContent = formatScore(score);

    main.appendChild(bar);
    main.appendChild(value);

    wrapper.appendChild(header);
    wrapper.appendChild(main);

    if (extra) {
        const extraEl = document.createElement("div");
        extraEl.className = "rc-day-card-extra";
        extraEl.textContent = extra;
        wrapper.appendChild(extraEl);
    }

    return wrapper;
}
