import { translate } from "./loader.js";
export { getLocale, loadTranslations } from "./loader.js";
export function t(key, params = {}) {
    return translate(key, params);
}
