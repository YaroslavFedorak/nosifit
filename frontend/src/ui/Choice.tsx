import { Check } from "lucide-react";
import { useId, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "../lib/cn";

export interface Option<T extends string> {
  id: T;
  label: string;
  /** A count or a short figure after the label. */
  note?: string;
}

function onArrowKeys<T extends string>(event: KeyboardEvent, options: Option<T>[], value: T, onChange: (id: T) => void): void {
  const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
  if (!step) return;
  event.preventDefault();
  const index = options.findIndex((item) => item.id === value);
  const next = options[(index + step + options.length) % options.length];
  if (next) onChange(next.id);
}

/**
 * Page-level tabs: text with a line under the current one. The row scrolls
 * sideways rather than wrapping when the labels do not fit.
 */
export function Tabs<T extends string>({
  options,
  value,
  onChange,
  label,
  className,
}: {
  options: Option<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  className?: string;
}) {
  const prefix = useId();
  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={(event) => onArrowKeys(event, options, value, onChange)}
      className={cn("flex gap-6 overflow-x-auto border-b border-rule [scrollbar-width:none]", className)}
    >
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            id={`${prefix}-${option.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.id)}
            className={cn(
              "relative min-h-tap min-w-tap shrink-0 whitespace-nowrap text-sm font-medium transition-colors duration-150",
              selected ? "text-ink" : "text-muted hover:text-ink-2",
            )}
          >
            {option.label}
            <span
              className={cn("absolute inset-x-0 -bottom-px h-0.5 bg-accent transition-opacity duration-150", selected ? "opacity-100" : "opacity-0")}
              aria-hidden="true"
            />
          </button>
        );
      })}
    </div>
  );
}

/**
 * A choice between a few, as a row of chips. The selected chip wears the
 * accent as a tint and an edge; the row scrolls when it has to.
 */
export function Chips<T extends string>({
  options,
  value,
  onChange,
  label,
  wrap = false,
  className,
}: {
  options: Option<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  wrap?: boolean;
  className?: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={(event) => onArrowKeys(event, options, value, onChange)}
      className={cn("flex gap-2", wrap ? "flex-wrap" : "-mx-4 overflow-x-auto px-4 [scrollbar-width:none]", className)}
    >
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.id)}
            className={cn(
              "press relative inline-flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-pill border px-3 text-sm font-medium after:absolute after:inset-x-0 after:-inset-y-1 after:content-['']",
              selected ? "border-tone-soft bg-tone-soft text-ink" : "border-rule text-ink-2 hover:bg-paper-3 hover:text-ink",
            )}
          >
            {option.label}
            {option.note && <span className="figure text-xs font-normal text-muted">{option.note}</span>}
          </button>
        );
      })}
    </div>
  );
}

/** On or off, applied at once. A checkbox underneath, so the platform handles the keyboard. */
export function Switch({
  checked,
  onChange,
  label,
  hint,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  hint?: string;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className={cn("flex min-h-tap items-center gap-4 py-2", disabled && "cursor-not-allowed opacity-55")}>
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{label}</span>
        {hint && <span className="mt-0.5 block text-sm text-muted">{hint}</span>}
      </span>
      <input
        id={id}
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="peer visually-hidden"
      />
      <span
        aria-hidden="true"
        className={cn(
          "relative h-7 w-12 shrink-0 rounded-pill transition-colors duration-200 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus",
          checked ? "bg-accent" : "bg-paper-4",
        )}
      >
        <span
          className={cn(
            "absolute left-1 top-1 size-5 rounded-pill transition-transform duration-200 ease-out",
            checked ? "translate-x-5 bg-accent-ink" : "bg-ink-2",
          )}
        />
      </span>
    </label>
  );
}

/** The round tick a habit or a finished set wears. Presentational: the row around it is the control. */
export function Tick({ checked, className }: { checked: boolean; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid size-6 shrink-0 place-items-center rounded-pill border-2 transition-colors duration-150",
        checked ? "border-tone bg-tone text-paper" : "border-edge text-transparent",
        className,
      )}
    >
      {checked && <Check size={14} strokeWidth={3.5} className="anim-tick" />}
    </span>
  );
}

/** A small quiet label for a state: "Сьогодні", "Активний". */
export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center rounded-pill bg-tone-soft px-2 py-0.5 text-xs font-medium text-ink", className)}>{children}</span>;
}
