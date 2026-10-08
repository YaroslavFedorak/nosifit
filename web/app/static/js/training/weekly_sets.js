import { getLocale, t } from "../i18n/index.js";
import { translateMuscle } from "./recommendations.js";
function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}
function isValidRow(row) {
    return (typeof row?.muscle === "string" &&
        Number.isFinite(row.sets) &&
        Number.isFinite(row.target_sets));
}
function fillPercent(sets, target) {
    if (target <= 0) {
        return sets > 0 ? 100 : 0;
    }
    // Above target the bar stays full; the number shows the surplus.
    return Math.min(100, Math.round((sets / target) * 100));
}
function renderState(body, title, text) {
    const state = element("div", "tr-rec-empty tr-weekly-sets-state");
    state.append(element("strong", "", title), element("span", "", text));
    body.replaceChildren(state);
}
function renderRow(row, format) {
    const name = translateMuscle(row.muscle);
    const sets = format.format(row.sets);
    const target = format.format(row.target_sets);
    const percent = fillPercent(row.sets, row.target_sets);
    const item = element("li", "tr-weekly-sets-row");
    if (row.target_sets > 0 && row.sets >= row.target_sets) {
        item.classList.add("is-reached");
    }
    const label = element("div", "tr-weekly-sets-label");
    label.append(element("span", "tr-weekly-sets-name", name), element("span", "tr-weekly-sets-value", `${sets} / ${target}`));
    const track = element("div", "tr-weekly-sets-track");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    track.setAttribute("aria-valuenow", String(percent));
    track.setAttribute("aria-label", t("weeklySets.ariaRow", {
        muscle: name,
        sets,
        target
    }));
    const fill = element("div", "tr-weekly-sets-fill");
    fill.style.width = `${percent}%`;
    track.append(fill);
    item.append(label, track);
    return item;
}
export function renderWeeklySets(data) {
    const body = document.getElementById("tr-weekly-sets-body");
    if (!body) {
        return;
    }
    body.removeAttribute("aria-busy");
    if (!data || !Array.isArray(data.muscles)) {
        renderState(body, t("weeklySets.loadErrorTitle"), t("weeklySets.loadErrorText"));
        return;
    }
    const rows = data.muscles.filter(isValidRow);
    if (!rows.some(row => row.sets > 0)) {
        renderState(body, t("weeklySets.emptyTitle"), t("weeklySets.emptyText"));
        return;
    }
    const format = new Intl.NumberFormat(getLocale(), {
        maximumFractionDigits: 1
    });
    const list = element("ul", "tr-weekly-sets-list");
    list.append(...rows.map(row => renderRow(row, format)));
    body.replaceChildren(list);
}
