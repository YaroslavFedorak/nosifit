export type Locale = "en" | "uk" | "pl" | "ru";

export const LOCALES: Locale[] = ["en", "uk", "pl", "ru"];

export interface Bootstrap {
  locale: Locale;
  user: { id: number; name: string } | null;
}

const FALLBACK: Bootstrap = { locale: "en", user: null };

/** The page the server rendered: language and the signed-in user (if any). */
function read(): Bootstrap {
  const node = document.getElementById("nosi-bootstrap");
  if (!node?.textContent) return FALLBACK;
  try {
    const raw = JSON.parse(node.textContent) as Partial<Bootstrap>;
    const locale = LOCALES.includes(raw.locale as Locale) ? (raw.locale as Locale) : "en";
    return { locale, user: raw.user ?? null };
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
