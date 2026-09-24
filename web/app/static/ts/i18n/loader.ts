import type {
Locale,
TranslationMap
} from "./types.js";

const SUPPORTED_LOCALES: Locale[] = [
"uk",
"en",
"pl",
"ru"
];

const DEFAULT_LOCALE: Locale = "uk";

const LOCALE_COOKIE =
"nosifit_locale";

let translations:
Record<string, TranslationMap> = {};

let currentLocale: Locale =
DEFAULT_LOCALE;

function getCookieLocale(): Locale | null {
const cookies =
document.cookie.split(";");

for (const cookie of cookies) {
    const [key, value] =
        cookie.trim().split("=");

    if (
        key === LOCALE_COOKIE &&
        SUPPORTED_LOCALES.includes(
            value as Locale
        )
    ) {
        return value as Locale;
    }
}

return null;

}

function getBrowserLocale(): Locale {
const languages = [
navigator.language,
...navigator.languages
];

for (const language of languages) {
    const locale =
        language
            .toLowerCase()
            .split("-")[0] as Locale;

    if (
        SUPPORTED_LOCALES.includes(
            locale
        )
    ) {
        return locale;
    }
}

return DEFAULT_LOCALE;

}

export function getLocale(): Locale {
return currentLocale;
}

export async function loadTranslations(
namespace: string
): Promise<void> {
const locale =
getCookieLocale() ??
getBrowserLocale();

currentLocale = locale;

const response =
    await fetch(
        `/api/i18n/${locale}/${namespace}`,
        {
            credentials: "same-origin"
        }
    );

if (!response.ok) {
    throw new Error(
        `Failed to load translations: ${namespace}`
    );
}

translations[namespace] =
    await response.json();

}

export function translate(
namespace: string,
key: string,
params: Record<string, string | number> = {}
): string {
const namespaceTranslations =
translations[namespace];

if (!namespaceTranslations) {
    return key;
}

const parts =
    key.split(".");

let value:
    | TranslationMap
    | string =
    namespaceTranslations;

for (const part of parts) {
    if (
        typeof value !== "object" ||
        value === null
    ) {
        return key;
    }

    value =
        value[part];
}

if (typeof value !== "string") {
    return key;
}

return value.replace(
    /\{(\w+)\}/g,
    (_, name: string) =>
        String(
            params[name] ??
            `{${name}}`
        )
);

}
