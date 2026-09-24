const SUPPORTED_LOCALES = [
    "uk",
    "en",
    "pl",
    "ru"
];
const DEFAULT_LOCALE = "uk";
const LOCALE_COOKIE = "nosifit_locale";
let translations = {};
let currentLocale = DEFAULT_LOCALE;
function getCookieLocale() {
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
        const [key, value] = cookie.trim().split("=");
        if (key === LOCALE_COOKIE &&
            SUPPORTED_LOCALES.includes(value)) {
            return value;
        }
    }
    return null;
}
function getBrowserLocale() {
    const languages = [
        navigator.language,
        ...navigator.languages
    ];
    for (const language of languages) {
        const locale = language
            .toLowerCase()
            .split("-")[0];
        if (SUPPORTED_LOCALES.includes(locale)) {
            return locale;
        }
    }
    return DEFAULT_LOCALE;
}
export function getLocale() {
    return currentLocale;
}
export async function loadTranslations(namespace) {
    const locale = getCookieLocale() ??
        getBrowserLocale();
    currentLocale = locale;
    const response = await fetch(`/api/i18n/${locale}/${namespace}`, {
        credentials: "same-origin"
    });
    if (!response.ok) {
        throw new Error(`Failed to load translations: ${namespace}`);
    }
    translations =
        await response.json();
}
export function translate(key, params = {}) {
    const parts = key.split(".");
    let value = translations;
    for (const part of parts) {
        if (typeof value !== "object" ||
            value === null) {
            return key;
        }
        value =
            value[part];
    }
    if (typeof value !== "string") {
        return key;
    }
    return value.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ??
        `{${name}}`));
}
