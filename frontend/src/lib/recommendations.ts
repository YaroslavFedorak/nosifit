import type { Recommendation } from "../api/types";
import type { ServerText } from "../i18n/server";

/** Title and sentence of a dashboard recommendation, in the user's language. */
export function describeRecommendation(rec: Recommendation, text: ServerText): { title: string; body: string } {
  const title =
    text.text(rec.title_key, rec.params) ?? (rec.slug ? text.exercise(rec.slug, rec.title ?? rec.slug) : (rec.title ?? ""));
  const raw = rec.description && !rec.description.startsWith("recommendations.") ? rec.description : "";
  const body = text.text(rec.description_key, rec.params) ?? raw;
  return { title, body };
}
