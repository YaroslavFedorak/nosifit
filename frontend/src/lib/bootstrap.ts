export type Locale = "en" | "uk" | "pl" | "ru";

export const LOCALES: Locale[] = ["en", "uk", "pl", "ru"];

export const LANGUAGE_NAMES: Record<Locale, string> = {
  en: "English",
  uk: "Українська",
  pl: "Polski",
  ru: "Русский",
};

export interface Bootstrap {
  locale: Locale;
  user: { id: number; name: string } | null;
  /** What this account may use; the server enforces each one as well. */
  features: { planGeneration: boolean };
  /** Version of the server texts: part of their URL, so the browser can keep them. */
  textVersion: string;
}

const FALLBACK: Bootstrap = { locale: "en", user: null, features: { planGeneration: false }, textVersion: "" };

/** The page the server rendered: language, the signed-in user (if any) and their features. */
function read(): Bootstrap {
  const node = document.getElementById("nosi-bootstrap");
  if (!node?.textContent) return FALLBACK;
  try {
    const raw = JSON.parse(node.textContent) as {
      locale?: string;
      user?: Bootstrap["user"];
      features?: { plan_generation?: boolean };
      text_version?: string;
    };
    const locale = LOCALES.includes(raw.locale as Locale) ? (raw.locale as Locale) : "en";
    return {
      locale,
      user: raw.user ?? null,
      features: { planGeneration: raw.features?.plan_generation === true },
      textVersion: typeof raw.text_version === "string" ? raw.text_version : "",
    };
  } catch {
    return FALLBACK;
  }
}

export const bootstrap: Bootstrap = read();

/** The language lives in a cookie the server already reads. */
export function switchLocale(locale: Locale): void {
  document.cookie = `nosifit_locale=${locale}; path=/; max-age=31536000; SameSite=Lax`;
  window.location.reload();
}
