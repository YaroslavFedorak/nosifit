import { ChevronDown, Minus, Plus } from "lucide-react";
import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { useT } from "../i18n";
import { cn } from "../lib/cn";
import { num, parseDecimal } from "../lib/format";
import { IconButton } from "./Button";

/** The look every text control shares; state moves colour and outline, never the border's width. */
export const controlClass =
  "min-h-control-lg w-full min-w-0 rounded-control border border-edge bg-paper-2 px-3 text-md text-ink outline-2 -outline-offset-2 outline-transparent transition-colors duration-150 placeholder:text-muted hover:bg-paper-3 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-55 aria-invalid:border-error";

interface FieldFrame {
  label: string;
  /** A format or a limit, shown under the field; an error takes its place. */
  hint?: string;
  error?: string | null;
  /** Hide the label visually when the field's purpose is plain from its surroundings. */
  hideLabel?: boolean;
  className?: string;
}

/** A label above, the control, and one reserved line below for a hint or an error. */
export function Field({
  label,
  hint,
  error,
  hideLabel = false,
  className,
  children,
}: FieldFrame & { children: (ids: { id: string; describedBy: string | undefined; invalid: boolean }) => ReactNode }) {
  const id = useId();
  const noteId = `${id}-note`;
  const note = error || hint;
  return (
    <div className={cn("min-w-0", className)}>
      <label htmlFor={id} className={hideLabel ? "visually-hidden" : "mb-1.5 block text-sm font-medium text-ink-2"}>
        {label}
      </label>
      {children({ id, describedBy: note ? noteId : undefined, invalid: Boolean(error) })}
      {note && (
        <p id={noteId} role={error ? "alert" : undefined} className={cn("mt-1 min-h-[1lh] text-sm", error ? "text-error" : "text-muted")}>
          {note}
        </p>
      )}
    </div>
  );
}

type TextFieldProps = FieldFrame & Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & { suffix?: string };

export function TextField({ label, hint, error, hideLabel, className, suffix, ...input }: TextFieldProps) {
  return (
    <Field label={label} hint={hint} error={error} hideLabel={hideLabel} className={className}>
      {({ id, describedBy, invalid }) => (
        <div className="relative">
          <input id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={cn(controlClass, suffix && "pr-12")} {...input} />
          {suffix && (
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted" aria-hidden="true">
              {suffix}
            </span>
          )}
        </div>
      )}
    </Field>
  );
}

type SelectFieldProps = FieldFrame & Omit<SelectHTMLAttributes<HTMLSelectElement>, "className"> & { children: ReactNode };

/** A native select: the platform's own picker on a phone, its own keyboard handling everywhere. */
export function SelectField({ label, hint, error, hideLabel, className, children, ...select }: SelectFieldProps) {
  return (
    <Field label={label} hint={hint} error={error} hideLabel={hideLabel} className={className}>
      {({ id, describedBy, invalid }) => (
        <div className="relative">
          <select id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={cn(controlClass, "appearance-none pr-10")} {...select}>
            {children}
          </select>
          <ChevronDown size={18} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
        </div>
      )}
    </Field>
  );
}

/**
 * A number with large minus and plus buttons beside it. The value stays text
 * while the user types, so "7," is not snapped back to "7".
 */
export function Stepper({
  label,
  value,
  onChange,
  step = 1,
  min = 0,
  max = 10000,
  decimals = 0,
  unit,
  hideLabel,
  autoFocus,
  className,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  step?: number;
  min?: number;
  max?: number;
  decimals?: number;
  unit?: string;
  hideLabel?: boolean;
  autoFocus?: boolean;
  className?: string;
}) {
  const { t } = useT();
  const bump = (direction: 1 | -1) => {
    const current = parseDecimal(value) ?? 0;
    const next = Math.min(max, Math.max(min, Math.round((current + direction * step) * 100) / 100));
    onChange(num(next, Math.max(decimals, 2)));
  };

  return (
    <Field label={label} hideLabel={hideLabel} className={className}>
      {({ id }) => (
        <div className="flex items-center gap-2">
          <IconButton tonal label={t("common.decrease")} className="size-control-lg" onClick={() => bump(-1)}>
            <Minus size={18} />
          </IconButton>
          <div className="relative min-w-0 flex-1">
            <input
              id={id}
              inputMode={decimals > 0 ? "decimal" : "numeric"}
              autoComplete="off"
              autoFocus={autoFocus}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onFocus={(event) => event.target.select()}
              className={cn(controlClass, "figure text-center text-lg", unit && "px-10")}
            />
            {unit && (
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted" aria-hidden="true">
                {unit}
              </span>
            )}
          </div>
          <IconButton tonal label={t("common.increase")} className="size-control-lg" onClick={() => bump(1)}>
            <Plus size={18} />
          </IconButton>
        </div>
      )}
    </Field>
  );
}
