import { useState } from "react";
import { entriesOf, isTimed } from "../../api/session";
import type { LoggedExercise, SetEntry } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Sheet } from "../../components/ui/Sheet";
import { parseDecimal, Stepper } from "../../components/ui/Stepper";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { clamp, num } from "../../lib/format";

/**
 * Edits one set, or adds one (`index === null`) that starts as a copy of the
 * last set. Mount it only while open: its fields start from the set being edited.
 */
export function SetSheet({
  exercise,
  index,
  onClose,
  onSave,
}: {
  exercise: LoggedExercise;
  index: number | null;
  onClose: () => void;
  onSave: (next: LoggedExercise) => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const timed = isTimed(exercise);
  const entries = entriesOf(exercise);
  const source = index === null ? entries[entries.length - 1] : entries[index];

  const [reps, setReps] = useState(num(source?.reps ?? 10, 0));
  const [seconds, setSeconds] = useState(num(source?.duration_sec ?? 30, 0));
  const [load, setLoad] = useState(num(source?.load ?? 0));

  const title = index === null ? t("tr.set.add") : t("tr.set.edit", { n: index + 1 });

  const commit = (list: SetEntry[]) => {
    const first = list[0];
    onSave({ ...exercise, set_entries: list, sets: list.length, reps: first?.reps ?? null, duration_sec: first?.duration_sec ?? null, load: first?.load ?? 0 });
    onClose();
  };

  const save = () => {
    const weight = clamp(parseDecimal(load) ?? 0, 0, 2000);
    const entry: SetEntry = timed
      ? { duration_sec: Math.round(clamp(parseDecimal(seconds) ?? 30, 1, 3600)), load: weight }
      : { reps: Math.round(clamp(parseDecimal(reps) ?? 10, 1, 100)), load: weight };
    commit(index === null ? [...entries, entry] : entries.map((item, position) => (position === index ? entry : item)));
  };

  const remove = () => commit(entries.filter((_, position) => position !== index));

  return (
    <Sheet
      open
      onClose={onClose}
      title={title}
      footer={
        <div className="flex gap-2">
          {index !== null && entries.length > 1 && (
            <Button variant="danger" onClick={remove}>
              {t("tr.set.remove")}
            </Button>
          )}
          <Button variant="primary" size="lg" className="flex-1" onClick={save}>
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <p className="pb-4 text-sm text-fg-muted">{text.exercise(exercise.slug, exercise.name)}</p>
      <div className="space-y-4">
        {timed ? (
          <Stepper label={t("tr.set.seconds")} value={seconds} onChange={setSeconds} step={5} min={1} max={3600} />
        ) : (
          <Stepper label={t("tr.set.reps")} value={reps} onChange={setReps} step={1} min={1} max={100} />
        )}
        {exercise.accepts_load !== false && (
          <Stepper label={t("tr.set.load")} value={load} onChange={setLoad} step={2.5} min={0} max={2000} decimals={1} />
        )}
      </div>
    </Sheet>
  );
}
