import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { LoggedExercise, SetEntry } from "../../api/types";
import { entriesOf, isTimed, withEntries } from "../../domain/training";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { clamp, num, parseDecimal } from "../../lib/format";
import { Button, IconButton } from "../../ui/Button";
import { controlClass } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

interface Draft {
  amount: string;
  load: string;
}

const toDraft = (entry: SetEntry, timed: boolean): Draft => ({
  amount: num(timed ? (entry.duration_sec ?? 30) : (entry.reps ?? 10), 0),
  load: entry.load ? num(entry.load) : "",
});

/**
 * The sets of one exercise, each a line of two numbers. Everything is
 * saved together with one button.
 */
export function ExerciseSheet({
  exercise,
  busy,
  onSave,
  onRemove,
  onClose,
}: {
  exercise: LoggedExercise;
  busy: boolean;
  onSave: (next: LoggedExercise) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const timed = isTimed(exercise);
  const withLoad = exercise.accepts_load !== false;
  const [sets, setSets] = useState<Draft[]>(() => entriesOf(exercise).map((entry) => toDraft(entry, timed)));

  const edit = (index: number, patch: Partial<Draft>) => setSets((list) => list.map((item, position) => (position === index ? { ...item, ...patch } : item)));

  const save = () => {
    const entries: SetEntry[] = sets.map((item) => {
      const load = clamp(parseDecimal(item.load) ?? 0, 0, 2000);
      return timed
        ? { duration_sec: Math.round(clamp(parseDecimal(item.amount) ?? 30, 1, 3600)), load }
        : { reps: Math.round(clamp(parseDecimal(item.amount) ?? 10, 1, 100)), load };
    });
    onSave(withEntries(exercise, entries));
  };

  return (
    <Sheet
      open
      onClose={onClose}
      title={text.exercise(exercise.slug, exercise.name)}
      footer={
        <div className="flex gap-2">
          <Button variant="danger" size="lg" disabled={busy} onClick={onRemove}>
            {t("exercise.remove")}
          </Button>
          <Button variant="primary" size="lg" className="flex-1" busy={busy} onClick={save}>
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <table className="w-full border-separate border-spacing-y-2">
        <thead>
          <tr className="text-left text-sm text-muted">
            <th scope="col" className="w-8 font-normal">
              <span className="visually-hidden">{t("set.number")}</span>
            </th>
            <th scope="col" className="font-normal">
              {timed ? t("set.seconds") : t("set.reps")}
            </th>
            {withLoad && (
              <th scope="col" className="font-normal">
                {t("set.load")}
              </th>
            )}
            <th scope="col" className="w-10">
              <span className="visually-hidden">{t("common.remove")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {sets.map((item, index) => (
            <tr key={index}>
              <td className="figure text-sm font-normal text-muted">{index + 1}</td>
              <td className="pr-2">
                <input
                  inputMode="numeric"
                  autoComplete="off"
                  aria-label={`${t("set.n", { n: index + 1 })}, ${timed ? t("set.seconds") : t("set.reps")}`}
                  value={item.amount}
                  onChange={(event) => edit(index, { amount: event.target.value })}
                  onFocus={(event) => event.target.select()}
                  className={`${controlClass} figure text-center`}
                />
              </td>
              {withLoad && (
                <td className="pr-1">
                  <input
                    inputMode="decimal"
                    autoComplete="off"
                    aria-label={`${t("set.n", { n: index + 1 })}, ${t("set.load")}`}
                    placeholder="0"
                    value={item.load}
                    onChange={(event) => edit(index, { load: event.target.value })}
                    onFocus={(event) => event.target.select()}
                    className={`${controlClass} figure text-center`}
                  />
                </td>
              )}
              <td>
                <IconButton label={t("set.remove", { n: index + 1 })} disabled={sets.length <= 1} onClick={() => setSets((list) => list.filter((_, position) => position !== index))}>
                  <Trash2 size={18} />
                </IconButton>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button
        variant="quiet"
        icon={<Plus size={16} aria-hidden="true" />}
        onClick={() => setSets((list) => [...list, { ...(list[list.length - 1] ?? { amount: timed ? "30" : "10", load: "" }) }])}
      >
        {t("set.add")}
      </Button>
    </Sheet>
  );
}
