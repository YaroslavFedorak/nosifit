import { useId, type ReactNode } from "react";
import { clamp } from "../../lib/format";

/** Circular progress. `value` is 0..1; the centre takes any content. */
export function Ring({
  value,
  size = 168,
  stroke = 12,
  label,
  from = "var(--color-training)",
  to = "var(--color-recovery)",
  glow = false,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label: string;
  from?: string;
  to?: string;
  glow?: boolean;
  children?: ReactNode;
}) {
  const gradient = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = clamp(value) * circumference;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        style={glow ? { filter: `drop-shadow(0 0 12px color-mix(in oklab, ${from} 45%, transparent))` } : undefined}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" style={{ stopColor: from }} />
            <stop offset="1" style={{ stopColor: to }} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgb(255 255 255 / 0.08)" strokeWidth={stroke} />
        {filled > 0 && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${gradient})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference}`}
          />
        )}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}
