import { cn } from "../../lib/cn";
import { clamp } from "../../lib/format";

export type BarTone = "accent" | "ok" | "warn" | "water";

const FILLS: Record<BarTone, string> = {
  accent: "bg-accent",
  ok: "bg-ok",
  warn: "bg-warn",
  water: "bg-water",
};

/** Thin progress bar. `value` is 0..1 (anything above fills it). */
export function Bar({
  value,
  tone = "accent",
  label,
  className,
}: {
  value: number;
  tone?: BarTone;
  label: string;
  className?: string;
}) {
  const filled = clamp(value);
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(filled * 100)}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-white/8", className)}
    >
      <div className={cn("h-full rounded-full transition-[width] duration-500", FILLS[tone])} style={{ width: `${filled * 100}%` }} />
    </div>
  );
}
