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

export const clamp = (value: number, min = 0, max = 1): number => Math.min(max, Math.max(min, value));

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

export function dateText(locale: Locale, date: Date, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(TAGS[locale], options).format(date);
}

export function splitMinutes(total: number): { h: number; m: number } {
  const rounded = Math.max(0, Math.round(total));
  return { h: Math.floor(rounded / 60), m: rounded % 60 };
}

export function timeOfDay(iso: string): string {
  const date = new Date(iso);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Percent of a goal, 0 when there is no goal. */
export function ratio(value: number | null | undefined, goal: number | null | undefined): number {
  if (!goal || !value) return 0;
  return value / goal;
}

/** Maps a 0-100 score onto the 0-4 activity levels used by the strips. */
export function levelFromScore(score: number | null | undefined): number {
  if (!score || score <= 0) return 0;
  if (score <= 25) return 1;
  if (score <= 50) return 2;
  if (score <= 75) return 3;
  return 4;
}
