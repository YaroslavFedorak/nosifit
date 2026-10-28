import { useId, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  icon?: ReactNode;
}

/**
 * Segmented control. Labels wrap instead of being cut off; `twoRows` lays four
 * tabs out as 2 × 2 on a phone and in one row from the tablet breakpoint up.
 */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  label,
  twoRows = false,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  twoRows?: boolean;
}) {
  const prefix = useId();

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const index = items.findIndex((item) => item.id === value);
    const next = items[(index + step + items.length) % items.length];
    if (next) onChange(next.id);
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn("grid gap-1 rounded-2xl border border-line bg-surface p-1", twoRows && "grid-cols-2 tab:grid-cols-4")}
      style={twoRows ? undefined : { gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
    >
      {items.map((item) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            id={`${prefix}-${item.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            className={cn(
              "inline-flex min-h-tap items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-center text-sm font-semibold leading-tight transition",
              selected ? "bg-surface-3 text-fg shadow-[inset_0_1px_0_rgb(255_255_255/0.06)]" : "text-fg-muted hover:text-fg",
            )}
          >
            {item.icon}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
