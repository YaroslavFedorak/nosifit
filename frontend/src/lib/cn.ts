export type ClassValue = string | false | null | undefined;

/** Joins class names, skipping the falsy ones. */
export function cn(...parts: ClassValue[]): string {
  return parts.filter(Boolean).join(" ");
}
