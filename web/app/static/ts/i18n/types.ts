export type Locale =
    | "uk"
    | "en"
    | "pl"
    | "ru";

export interface TranslationMap {
    [key: string]: string | TranslationMap;
}

export type TranslationValue =
    string | TranslationMap;