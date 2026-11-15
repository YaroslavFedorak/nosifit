import { useState } from "react";
import { useLogSleep } from "../../api/mutations";
import { useRecoverySnapshot } from "../../api/queries";
import { useT } from "../../i18n";
import { splitMinutes, timeOfDay } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Field, controlClass } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

/** Wake-up is today; bedtime is the latest earlier moment with that clock time. */
function rangeOf(bedtime: string, wake: string): { start: Date; end: Date } | null {
  const [bedHour, bedMinute] = bedtime.split(":").map(Number);
  const [wakeHour, wakeMinute] = wake.split(":").map(Number);
  if ([bedHour, bedMinute, wakeHour, wakeMinute].some((part) => part === undefined || Number.isNaN(part))) return null;
  const end = new Date();
  end.setHours(wakeHour ?? 0, wakeMinute ?? 0, 0, 0);
  const start = new Date(end);
  start.setHours(bedHour ?? 0, bedMinute ?? 0, 0, 0);
  if (start >= end) start.setDate(start.getDate() - 1);
  return { start, end };
}

/**
 * Last night's sleep in two fields. They start from the user's own last
 * bedtime and wake-up, so a regular sleeper only confirms.
 */
export function SleepSheet({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const snapshot = useRecoverySnapshot();
  const log = useLogSleep();
  const last = snapshot.data;
  const [bedtime, setBedtime] = useState(() => (last?.sleep_start ? timeOfDay(last.sleep_start) : "23:00"));
  const [wake, setWake] = useState(() => (last?.sleep_end ? timeOfDay(last.sleep_end) : "07:00"));

  const range = rangeOf(bedtime, wake);
  const minutes = range ? (range.end.getTime() - range.start.getTime()) / 60000 : 0;
  const { h, m } = splitMinutes(minutes);

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("sleep.title")}
      footer={
        <Button variant="primary" size="lg" block disabled={!range} busy={log.isPending} onClick={() => range && log.mutate(range, { onSuccess: onClose })}>
          {t("common.save")}
        </Button>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("sleep.bed")}>
          {({ id }) => (
            <input id={id} type="time" value={bedtime} onChange={(event) => setBedtime(event.target.value)} className={`${controlClass} figure text-center text-lg`} />
          )}
        </Field>
        <Field label={t("sleep.wake")}>
          {({ id }) => (
            <input id={id} type="time" value={wake} onChange={(event) => setWake(event.target.value)} className={`${controlClass} figure text-center text-lg`} />
          )}
        </Field>
      </div>
      <p className="mt-4 text-sm text-muted" aria-live="polite">
        {range ? t("sleep.total", { h, m }) : t("sleep.pickTimes")}
      </p>
    </Sheet>
  );
}
