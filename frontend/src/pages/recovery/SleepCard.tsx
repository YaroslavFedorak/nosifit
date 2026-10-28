import { Moon } from "lucide-react";
import { useId, useState } from "react";
import { useLogSleep } from "../../api/mutations";
import type { RecoverySnapshot } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Chip } from "../../components/ui/Chip";
import { Sheet } from "../../components/ui/Sheet";
import { useT } from "../../i18n";
import { splitMinutes, timeOfDay } from "../../lib/format";
import { toast } from "../../lib/toast";

/** Wake-up is today; bedtime is the latest earlier moment with that clock time. */
function rangeOf(bedtime: string, wake: string): { start: Date; end: Date } {
  const [bedHour = 0, bedMinute = 0] = bedtime.split(":").map(Number);
  const [wakeHour = 0, wakeMinute = 0] = wake.split(":").map(Number);
  const end = new Date();
  end.setHours(wakeHour, wakeMinute, 0, 0);
  const start = new Date(end);
  start.setHours(bedHour, bedMinute, 0, 0);
  if (start >= end) start.setDate(start.getDate() - 1);
  return { start, end };
}

function TimeField({ label, value, onChange }: { label: string; value: string; onChange: (next: string) => void }) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-fg-muted">
        {label}
      </label>
      <input
        id={id}
        type="time"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-tap-lg w-full rounded-xl border border-line-strong bg-surface-2 px-3 text-center text-xl font-semibold tabular-nums outline-none focus:border-fg/40"
      />
    </div>
  );
}

function SleepSheet({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const log = useLogSleep();
  const [bedtime, setBedtime] = useState("23:00");
  const [wake, setWake] = useState("07:00");

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("rc.sleep.log")}
      footer={
        <Button
          variant="primary"
          size="lg"
          block
          disabled={!bedtime || !wake || log.isPending}
          onClick={() =>
            log.mutate(rangeOf(bedtime, wake), {
              onSuccess: () => {
                toast(t("common.saved"));
                onClose();
              },
            })
          }
        >
          {t("common.save")}
        </Button>
      }
    >
      <div className="grid grid-cols-2 gap-3 pt-2">
        <TimeField label={t("rc.sleep.bed")} value={bedtime} onChange={setBedtime} />
        <TimeField label={t("rc.sleep.wake")} value={wake} onChange={setWake} />
      </div>
    </Sheet>
  );
}

export function SleepCard({ snapshot, openInitially }: { snapshot: RecoverySnapshot; openInitially: boolean }) {
  const { t } = useT();
  const [open, setOpen] = useState(openInitially);
  const minutes = snapshot.sleep_duration_minutes ?? 0;
  const { h, m } = splitMinutes(minutes);

  return (
    <Card accent="recovery" aria-labelledby="sleep-title">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="sleep-title" className="text-base font-semibold">
            {t("rc.sleep.title")}
          </h2>
          <p className="mt-0.5 text-sm text-fg-muted">{t("rc.sleep.last")}</p>
        </div>
        <Button icon={<Moon size={16} aria-hidden="true" />} onClick={() => setOpen(true)}>
          {t("rc.sleep.log")}
        </Button>
      </div>

      {minutes > 0 ? (
        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
          <div>
            <p className="text-3xl font-semibold leading-none tracking-tight tabular-nums">
              {h} <span className="text-base font-medium text-fg-muted">{t("unit.h")}</span> {m}{" "}
              <span className="text-base font-medium text-fg-muted">{t("unit.min")}</span>
            </p>
            {snapshot.sleep_start && snapshot.sleep_end && (
              <p className="mt-2 text-sm tabular-nums text-fg-muted">
                {timeOfDay(snapshot.sleep_start)} → {timeOfDay(snapshot.sleep_end)}
              </p>
            )}
          </div>
          {snapshot.sleep_score != null && <Chip tone="accent">{t("rc.sleep.quality", { n: Math.round(snapshot.sleep_score) })}</Chip>}
        </div>
      ) : (
        <p className="mt-4 text-sm text-fg-muted">{t("rc.sleep.none")}</p>
      )}

      {open && <SleepSheet onClose={() => setOpen(false)} />}
    </Card>
  );
}
