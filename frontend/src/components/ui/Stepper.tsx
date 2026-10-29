import { Minus, Plus } from "lucide-react";
import { useId } from "react";
import { useT } from "../../i18n";
import { num } from "../../lib/format";
import { IconButton } from "./Button";

/** Accepts "7.5" and "7,5"; null when the text is not a number. */
export function parseDecimal(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed.replace(",", "."));
  return Number.isNaN(value) ? null : value;
}

/** Number field with large − and + buttons. The value is kept as text while typing. */
export function Stepper({
  label,
  value,
  onChange,
  step = 1,
  min = 0,
  max = 10000,
  decimals = 0,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  step?: number;
  min?: number;
  max?: number;
  decimals?: number;
}) {
  const { t } = useT();
  const id = useId();

  const bump = (direction: 1 | -1) => {
    const current = parseDecimal(value) ?? 0;
    const next = Math.min(max, Math.max(min, Math.round((current + direction * step) * 100) / 100));
    onChange(num(next, Math.max(decimals, 2)));
  };

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-fg-muted">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <IconButton label={t("common.decrease")} className="border border-line-strong bg-surface-2" onClick={() => bump(-1)}>
          <Minus size={18} />
        </IconButton>
        <input
          id={id}
          inputMode="decimal"
          autoComplete="off"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-tap-lg w-full min-w-0 rounded-xl border border-line-strong bg-surface-2 px-3 text-center text-xl font-semibold tabular-nums outline-none focus:border-fg/40"
        />
        <IconButton label={t("common.increase")} className="border border-line-strong bg-surface-2" onClick={() => bump(1)}>
          <Plus size={18} />
        </IconButton>
      </div>
    </div>
  );
}
