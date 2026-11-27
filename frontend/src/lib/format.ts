import type { Locale } from "./bootstrap";

const TAGS: Record<Locale, string> = { en: "en-GB", uk: "uk-UA", pl: "pl-PL", ru: "ru-RU" };

const numberFormats = new Map<number, Intl.NumberFormat>();

/**
 * One decimal separator for every number in every language: a dot ("78.4").
 * The API's own sentences use dots too, so the screen never mixes the two.
 */
export function num(value: number | null | undefined, maxDecimals = 1): string {
  if (value == null || Number.isNaN(value)) return "–";
  let format = numberFormats.get(maxDecimals);
  if (!format) {
    format = new Intl.NumberFormat("en-US", { maximumFractionDigits: maxDecimals, useGrouping: false });
    numberFormats.set(maxDecimals, format);
  }
  return format.format(value);
}

/** Accepts "7.5" and "7,5"; null when the text is not a number. */
export function parseDecimal(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed.replace(",", "."));
  return Number.isFinite(value) ? value : null;
}

export const clamp = (value: number, min = 0, max = 1): number => Math.min(max, Math.max(min, value));

/** Sentence case for text that starts lower case, such as a weekday: "Четвер, 29 жовтня". */
export const capitalize = (text: string): string => text.charAt(0).toLocaleUpperCase() + text.slice(1);

const pad = (n: number): string => String(n).padStart(2, "0");

/** Local calendar day as YYYY-MM-DD. */
export function isoDay(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseDay(iso: string): Date {
  const [year = 1970, month = 1, day = 1] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

const dateFormats = new Map<string, Intl.DateTimeFormat>();

/**
 * A date in the page's language. Building an Intl.DateTimeFormat costs far
 * more than using one, and a calendar formats hundreds of days, so each
 * language and set of options is built once and kept.
 */
export function dateText(locale: Locale, date: Date, options: Intl.DateTimeFormatOptions): string {
  const key = `${locale}|${JSON.stringify(options)}`;
  let format = dateFormats.get(key);
  if (!format) {
    format = new Intl.DateTimeFormat(TAGS[locale], options);
    dateFormats.set(key, format);
  }
  return format.format(date);
}

/** "Четвер, 12 листопада" */
export const longDay = (locale: Locale, date: Date): string =>
  capitalize(dateText(locale, date, { weekday: "long", day: "numeric", month: "long" }));

/** "Чт, 12 лист." */
export const shortDay = (locale: Locale, date: Date): string =>
  capitalize(dateText(locale, date, { weekday: "short", day: "numeric", month: "short" }));

/** One or two letters of a weekday, for chart axes. */
export const weekdayLetter = (locale: Locale, date: Date): string => capitalize(dateText(locale, date, { weekday: "short" })).slice(0, 2);

export function splitMinutes(total: number): { h: number; m: number } {
  const rounded = Math.max(0, Math.round(total));
  return { h: Math.floor(rounded / 60), m: rounded % 60 };
}

export function timeOfDay(iso: string): string {
  const date = new Date(iso);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** "23:10 – 06:30" */
export const timeRange = (startIso: string, endIso: string): string => `${timeOfDay(startIso)} – ${timeOfDay(endIso)}`;

/** "1:05" for a countdown of seconds. */
export function clock(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${pad(whole % 60)}`;
}

/** Share of a goal, 0 when there is no goal. */
export function ratio(value: number | null | undefined, goal: number | null | undefined): number {
  if (!goal || !value) return 0;
  return value / goal;
}

/** Maps a 0-100 score onto the 0-4 activity levels used by the calendar. */
export function levelFromScore(score: number | null | undefined): number {
  if (!score || score <= 0) return 0;
  if (score <= 25) return 1;
  if (score <= 50) return 2;
  if (score <= 75) return 3;
  return 4;
}
