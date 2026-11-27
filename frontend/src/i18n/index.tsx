import { createContext, use, useMemo, type ReactNode } from "react";
import { bootstrap, type Locale } from "../lib/bootstrap";
import { num } from "../lib/format";
import type { TKey } from "./en";

export type Params = Record<string, string | number>;

/** The counted nouns: "count.sets" has the forms "count.sets.one", "count.sets.few" and so on. */
type PluralKey = Extract<TKey, `count.${string}.other`>;
export type PluralBase = PluralKey extends `${infer Base}.other` ? Base : never;

export interface I18n {
  locale: Locale;
  t: (key: TKey, params?: Params) => string;
  /** Plural-aware count: tn("count.sets", 3) gives "3 sets" or "3 підходи". */
  tn: (base: PluralBase, n: number) => string;
}

export type Dictionary = Record<string, string>;

// One file per language, and a page loads only its own (the server preloads
// it next to the bundle). Every dictionary has every key: the types of uk,
// pl and ru require each key of en, so no page needs a second language.
const loaders: Record<Locale, () => Promise<Dictionary>> = {
  en: () => import("./en").then((module) => module.en),
  uk: () => import("./uk").then((module) => module.uk),
  pl: () => import("./pl").then((module) => module.pl),
  ru: () => import("./ru").then((module) => module.ru),
};

export function loadDictionary(locale: Locale): Promise<Dictionary> {
  return (loaders[locale] ?? loaders.en)();
}

export function interpolate(text: string, params?: Params): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match));
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ dictionary, children }: { dictionary: Dictionary; children: ReactNode }) {
  const value = useMemo<I18n>(() => {
    // The plural rules must belong to the language whose words are used.
    const rules = new Intl.PluralRules(bootstrap.locale);
    const lookup = (key: string): string => dictionary[key] ?? key;
    return {
      locale: bootstrap.locale,
      t: (key, params) => interpolate(lookup(key), params),
      tn: (base, n) => {
        const form = `${base}.${rules.select(n)}`;
        const text = form in dictionary ? lookup(form) : lookup(`${base}.other`);
        return interpolate(text, { n: num(n, 0) });
      },
    };
  }, [dictionary]);
  return <I18nContext value={value}>{children}</I18nContext>;
}

export function useT(): I18n {
  const value = use(I18nContext);
  if (!value) throw new Error("useT must be used inside <I18nProvider>");
  return value;
}
