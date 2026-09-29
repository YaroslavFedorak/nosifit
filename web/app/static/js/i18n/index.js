import { translate, } from "./loader.js";
export { getLocale, loadTranslations, } from "./loader.js";
export function t(key, params = {}) {
    return translate("training", key, params);
}
export function common_t(key, params = {}) {
    return translate("common", key, params);
}
export function auth_t(key, params = {}) {
    return translate("auth", key, params);
}
export function public_t(key, params = {}) {
    return translate("public", key, params);
}
export function app_t(key, params = {}) {
    return translate("app", key, params);
}
export function dashboard_t(key, params = {}) {
    return translate("dashboard", key, params);
}
export function exercise_t(slug) {
    return translate("exercises", `${slug}.name`);
}
export function recovery_t(key, params = {}) {
    return translate("recovery", key, params);
}
export function nutrition_t(key, params = {}) {
    return translate("nutrition", key, params);
}
export function profile_t(key, params = {}) {
    return translate("profile", key, params);
}
