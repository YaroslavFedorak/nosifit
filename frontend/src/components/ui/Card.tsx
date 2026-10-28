import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export type Accent = "training" | "nutrition" | "recovery" | "water";
export type CardTone = "flat" | "hero" | "glass";

interface CardStyle {
  accent?: Accent;
  tone?: CardTone;
  padded?: boolean;
}

/** Class list shared by <Card> and by links that look like cards. */
export function cardClass({ accent, tone = "flat", padded = true }: CardStyle = {}): string {
  return cn(
    "relative block overflow-hidden rounded-2xl",
    tone === "flat" && "border border-line bg-surface",
    tone === "hero" && "surface-hero",
    tone === "glass" && "surface-glass",
    accent && "accent-strip",
    padded && "p-4 tab:p-5",
  );
}

type CardProps = HTMLAttributes<HTMLElement> & CardStyle & { as?: "section" | "div" | "article" | "li" };

/**
 * Flat by default. Depth (`hero`, `glass`) is meant for the one or two primary
 * status cards on a page; the accent strip marks which module a card belongs to.
 */
export function Card({ as: Tag = "section", accent, tone, padded, className, ...rest }: CardProps) {
  return <Tag data-accent={accent} className={cn(cardClass({ accent, tone, padded }), className)} {...rest} />;
}
