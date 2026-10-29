import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export type Accent = "training" | "nutrition" | "recovery" | "water";
export type CardTone = "flat" | "hero" | "glass";

interface CardStyle {
  accent?: Accent;
  tone?: CardTone;
  padded?: boolean;
  /** The module colour along the top edge, only where cards of different modules sit together. */
  strip?: boolean;
}

/** Class list shared by <Card> and by links that look like cards. */
export function cardClass({ accent, tone = "flat", padded = true, strip = false }: CardStyle = {}): string {
  return cn(
    "relative block overflow-hidden rounded-2xl",
    tone === "flat" && "border border-line bg-surface",
    tone === "hero" && "surface-hero",
    tone === "glass" && "surface-glass",
    accent && strip && "accent-strip",
    padded && "p-4 tab:p-5",
  );
}

type CardProps = HTMLAttributes<HTMLElement> & CardStyle & { as?: "section" | "div" | "article" | "li" };

/**
 * Flat by default. Depth (`hero`, `glass`) is meant for the one or two primary
 * status cards on a page. `accent` sets the module colour for what is inside; `strip` also draws it along
 * the top, which only says something where modules sit side by side or on a page's lead card.
 */
export function Card({ as: Tag = "section", accent, tone, padded, strip, className, ...rest }: CardProps) {
  return <Tag data-accent={accent} className={cn(cardClass({ accent, tone, padded, strip }), className)} {...rest} />;
}
