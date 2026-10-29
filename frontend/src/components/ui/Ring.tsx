import type { ReactNode } from "react";
import { cn } from "../../lib/cn";
import { clamp } from "../../lib/format";

/**
 * Circular progress in one colour: the module's accent unless told otherwise.
 * `value` is 0..1; the centre takes any content. The glow falls below the
 * ring, like the one under the hero card. A `className` may size the ring per
 * breakpoint instead of `size`; the drawing scales with it.
 */
export function Ring({
  value,
  size = 168,
  stroke = 12,
  label,
  color = "var(--accent, var(--color-training))",
  glow = false,
  className,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label: string;
  color?: string;
  glow?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = clamp(value) * circumference;

  return (
    <div
      className={cn("relative shrink-0", className)}
      style={className ? undefined : { width: size, height: size }}
      role="img"
      aria-label={label}
    >
      <div
        className="absolute inset-0"
        style={glow ? { filter: `drop-shadow(0 6px 14px color-mix(in oklab, ${color} 40%, transparent))` } : undefined}
        aria-hidden="true"
      >
        <svg width="100%" height="100%" viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} style={{ stroke: "var(--color-track)" }} />
          {filled > 0 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${filled} ${circumference}`}
              style={{ stroke: color }}
            />
          )}
        </svg>
      </div>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}
