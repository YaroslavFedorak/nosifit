import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export type Tone = "neutral" | "ok" | "warn" | "danger" | "accent";

const TONES: Record<Tone, string> = {
  neutral: "border-line bg-surface-2 text-fg-muted",
  ok: "border-ok/25 bg-ok/10 text-ok",
  warn: "border-warn/25 bg-warn/10 text-warn",
  danger: "border-danger/25 bg-danger/10 text-danger",
  accent: "chip-accent",
};

export function Chip({
  tone = "neutral",
  icon,
  children,
  className,
}: {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}

/** Tiny label: the one place text may go below 12px. */
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 text-badge font-semibold uppercase tracking-wide",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}
