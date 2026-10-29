import { Ellipsis, Plus } from "lucide-react";
import { useState } from "react";
import { entriesOf, isTimed } from "../../api/session";
import type { LoggedExercise, SetEntry } from "../../api/types";
import { Button, IconButton } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { useT, type I18n } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { num } from "../../lib/format";

export function setLabel(entry: SetEntry, timed: boolean, t: I18n["t"]): string {
  if (timed) return `${entry.duration_sec ?? 0} ${t("unit.s")}`;
  const load = entry.load ?? 0;
  return load > 0 ? `${entry.reps ?? 0} × ${num(load)} ${t("unit.kg")}` : `${entry.reps ?? 0} ${t("unit.reps")}`;
}

const CHIP =
  "inline-flex min-h-tap min-w-tap items-center justify-center rounded-xl border px-3 text-sm font-semibold tabular-nums transition active:scale-95 disabled:opacity-50";

/**
 * One exercise as a card. Its sets are chips that wrap onto as many rows as
 * they need, each at least 44px tall, so rows can never run into each other.
 */
export function ExerciseCard({
  exercise,
  disabled,
  onEditSet,
  onAddSet,
  onRemove,
}: {
  exercise: LoggedExercise;
  disabled: boolean;
  onEditSet: (index: number) => void;
  onAddSet: () => void;
  onRemove: () => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const [confirming, setConfirming] = useState(false);
  const timed = isTimed(exercise);
  const entries = entriesOf(exercise);

  return (
    <Card as="li" className="min-w-0 grow basis-[17rem] space-y-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 pt-2.5 text-base font-semibold leading-snug">{text.exercise(exercise.slug, exercise.name)}</h3>
        <IconButton label={t("tr.ex.menu")} aria-expanded={confirming} onClick={() => setConfirming((open) => !open)} className="-mr-1 -mt-1">
          <Ellipsis size={20} />
        </IconButton>
      </div>

      <div className="flex flex-wrap gap-2">
        {entries.map((entry, index) => (
          <button
            key={index}
            type="button"
            disabled={disabled}
            aria-label={`${t("tr.set.n", { n: index + 1 })}: ${setLabel(entry, timed, t)}`}
            onClick={() => onEditSet(index)}
            className={`${CHIP} border-line-strong bg-surface-2 text-fg hover:bg-surface-3`}
          >
            {setLabel(entry, timed, t)}
          </button>
        ))}
        <button
          type="button"
          disabled={disabled}
          aria-label={t("tr.set.add")}
          onClick={onAddSet}
          className={`${CHIP} border-dashed border-line-strong text-fg-muted hover:text-fg`}
        >
          <Plus size={18} aria-hidden="true" />
        </button>
      </div>

      {confirming && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-danger/25 bg-danger/10 p-2 pl-3">
          <span className="text-sm font-medium">{t("tr.ex.confirm")}</span>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="danger" disabled={disabled} onClick={onRemove}>
              {t("common.remove")}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
