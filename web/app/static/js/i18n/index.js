import { translate } from "./loader.js";
export { getLocale, loadTranslations } from "./loader.js";
export function t(key, params = {}) {
    return translate("training", key, params);
}
export function exercise_t(slug) {
    return translate("exercises", `${slug}.name`);
}
