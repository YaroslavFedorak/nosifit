import type { I18n } from "../../i18n";

/** "g", "ml" and "pcs" in the interface language; any other unit as it is. */
export function unitLabel(unit: string, t: I18n["t"]): string {
  return unit === "g" ? t("unit.g") : unit === "ml" ? t("unit.ml") : unit === "pcs" ? t("unit.pcs") : unit;
}
