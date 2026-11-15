import type { Tone } from "../design/tokens";
import { cn } from "../lib/cn";
import { clamp } from "../lib/format";

/** A thin bar for one value against its goal. `value` is 0..1; anything above fills it. */
export function Progress({ value, label, tone, className }: { value: number; label: string; tone?: Tone; className?: string }) {
  const filled = clamp(value);
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(filled * 100)}
      data-tone={tone}
      className={cn("h-1.5 w-full overflow-hidden rounded-pill bg-paper-4", className)}
    >
      <div
        className="h-full w-full origin-left rounded-pill bg-tone transition-transform duration-500 ease-out"
        style={{ transform: `scaleX(${filled})` }}
      />
    </div>
  );
}

export interface BarDatum {
  key: string;
  /** Axis label under the bar. */
  label: string;
  /** null = nothing recorded that day: no bar, not a bar of zero. */
  value: number | null;
  /** What a screen reader hears, and the tooltip. */
  title: string;
  current?: boolean;
}

/**
 * A handful of values over days: one bar each, a hairline for the goal.
 * Days without a record leave their slot empty.
 */
export function Bars({
  data,
  goal,
  tone,
  label,
  onPick,
  className,
}: {
  data: BarDatum[];
  goal?: number | null;
  tone?: Tone;
  label: string;
  onPick?: (key: string) => void;
  className?: string;
}) {
  const top = Math.max(goal ?? 0, ...data.map((item) => item.value ?? 0), 1) * 1.08;
  return (
    <div data-tone={tone} role="group" aria-label={label} className={cn("relative", className)}>
      <div className="relative flex h-24 items-end gap-1">
        {goal ? <span className="absolute inset-x-0 border-t border-edge" style={{ bottom: `${(goal / top) * 100}%` }} aria-hidden="true" /> : null}
        {data.map((item) => {
          const share = item.value == null ? 0 : Math.max(0.03, item.value / top);
          const bar = (
            <span
              className={cn("block w-full max-w-6 rounded-t-[2px]", item.value == null ? "h-0" : item.current ? "bg-tone" : "bg-tone opacity-55")}
              style={item.value == null ? undefined : { height: `${share * 100}%` }}
            />
          );
          return onPick ? (
            <button
              key={item.key}
              type="button"
              title={item.title}
              aria-label={item.title}
              onClick={() => onPick(item.key)}
              className="relative flex h-full min-w-0 flex-1 items-end justify-center rounded-[2px] hover:bg-paper-3"
            >
              {bar}
            </button>
          ) : (
            <span key={item.key} role="img" aria-label={item.title} title={item.title} className="relative flex h-full min-w-0 flex-1 items-end justify-center">
              {bar}
            </span>
          );
        })}
      </div>
      <div className="mt-1.5 flex gap-1 border-t border-rule pt-1.5" aria-hidden="true">
        {data.map((item) => (
          <span key={item.key} className={cn("min-w-0 flex-1 text-center text-xs", item.current ? "font-medium text-ink" : "text-muted")}>
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/** A trend at a glance: a line through the values, no axes. */
export function Sparkline({ values, label, tone, className }: { values: number[]; label: string; tone?: Tone; className?: string }) {
  if (values.length < 2) return null;
  const width = 120;
  const height = 36;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * (width - 4) + 2;
    const y = height - 3 - ((value - min) / span) * (height - 6);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const last = points[points.length - 1]?.split(",") ?? ["0", "0"];
  return (
    <svg data-tone={tone} role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} className={cn("h-9 w-[7.5rem]", className)}>
      <polyline points={points.join(" ")} fill="none" className="stroke-tone" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="3" className="fill-tone" />
    </svg>
  );
}
