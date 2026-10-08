import { getLocale } from "../i18n/index.js";
export function renderCurrentDate() {
    const element = document.getElementById("current-date");
    if (!element) {
        return;
    }
    const date = new Date();
    element.textContent =
        date.toLocaleDateString(getLocale(), {
            weekday: "long",
            day: "numeric",
            month: "long"
        });
}
