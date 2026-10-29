import { createContext, use, useMemo, type ReactNode } from "react";
import { bootstrap, type Locale } from "../lib/bootstrap";
import { num } from "../lib/format";
import { en, type TKey } from "./en";
import { uk } from "./uk";

export type Params = Record<string, string | number>;
export type PluralBase = "count.exercises" | "count.sets" | "count.hardSets" | "count.days";

export interface I18n {
  locale: Locale;
  t: (key: TKey, params?: Params) => string;
  /** Plural-aware count: tn("count.sets", 3) gives "3 sets" or "3 підходи". */
  tn: (base: PluralBase, n: number) => string;
}

// Polish and Russian fall back to English until their dictionaries exist.
const dictionaries: Partial<Record<Locale, Record<string, string>>> = { en, uk };

export function interpolate(text: string, params?: Params): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match));
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const value = useMemo<I18n>(() => {
    const dictionary: Record<string, string> = dictionaries[bootstrap.locale] ?? en;
    const rules = new Intl.PluralRules(bootstrap.locale);
    const lookup = (key: string): string => dictionary[key] ?? (en as Record<string, string>)[key] ?? key;
    return {
      locale: bootstrap.locale,
      t: (key, params) => interpolate(lookup(key), params),
      tn: (base, n) => {
        const form = `${base}.${rules.select(n)}`;
        const text = form in dictionary ? lookup(form) : lookup(`${base}.other`);
        return interpolate(text, { n: num(n, 0) });
      },
    };
  }, []);
  return <I18nContext value={value}>{children}</I18nContext>;
}

export function useT(): I18n {
  const value = use(I18nContext);
  if (!value) throw new Error("useT must be used inside <I18nProvider>");
  return value;
}
