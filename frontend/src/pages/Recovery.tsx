import { HeartPulse } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { useRecoveryHeatmap, useRecoverySnapshot } from "../api/queries";
import type { RecoveryTip } from "../api/types";
import { ActivityStrip, STRIP_DAYS } from "../components/ui/ActivityStrip";
import { Button } from "../components/ui/Button";
import { CalendarSheet, type CalendarDay } from "../components/ui/CalendarSheet";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { ErrorState, Skeleton } from "../components/ui/States";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { addDays, isoDay, levelFromScore } from "../lib/format";
import { useTitle } from "../lib/useTitle";
import { HabitsCard } from "./recovery/HabitsCard";
import { SleepCard } from "./recovery/SleepCard";
import { VitalsCard } from "./recovery/VitalsCard";

const TIP_LIMIT = 2;

function Tips({ tips }: { tips: RecoveryTip[] }) {
  const { t } = useT();
  const text = useServerText();
  const [all, setAll] = useState(false);

  const entries = tips
    .map((tip) => {
      const muscle = typeof tip.params.muscle === "string" ? text.muscle(tip.params.muscle).toLowerCase() : undefined;
      const params = muscle ? { ...tip.params, muscle } : tip.params;
      return { tip, title: text.text(tip.title_key, params), body: text.text(tip.message_key, params) };
    })
    .filter((entry) => entry.title);
  if (entries.length === 0) return null;

  return (
    <Card accent="recovery" aria-labelledby="rc-tips-title">
      <h2 id="rc-tips-title" className="text-base font-semibold">
        {t("rc.tips")}
      </h2>
      <ul className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-2.5">
        {(all ? entries : entries.slice(0, TIP_LIMIT)).map(({ tip, title, body }) => (
          <li key={tip.id} className="rounded-xl border border-line bg-surface-2/50 p-3.5">
            <h3 className="text-sm font-semibold leading-snug">{title}</h3>
            {body && <p className="mt-1 text-sm text-fg-muted">{body}</p>}
          </li>
        ))}
      </ul>
      {entries.length > TIP_LIMIT && (
        <Button variant="ghost" block className="mt-3" aria-expanded={all} onClick={() => setAll((value) => !value)}>
          {all ? t("common.showLess") : t("common.showMore")}
        </Button>
      )}
    </Card>
  );
}

export default function Recovery() {
  const { t, tn } = useT();
  useTitle(t("nav.recovery"));
  const [params] = useSearchParams();
  const snapshot = useRecoverySnapshot();
  const heatmap = useRecoveryHeatmap();
  const [calendar, setCalendar] = useState(false);

  const { strip, calendarDays } = useMemo(() => {
    const days = heatmap.data ?? [];
    const byDate = new Map(days.map((day) => [day.date, levelFromScore(day.recovery_score)]));
    const last = new Date();
    return {
      strip: Array.from({ length: STRIP_DAYS }, (_, index) => byDate.get(isoDay(addDays(last, index - (STRIP_DAYS - 1)))) ?? 0),
      calendarDays: days.map<CalendarDay>((day) => ({
        date: day.date,
        level: levelFromScore(day.recovery_score),
        note: day.recovery_score != null ? `${t("rc.score")}: ${Math.round(day.recovery_score)}` : undefined,
      })),
    };
  }, [heatmap.data, t]);

  return (
    <div data-accent="recovery">
      <PageHeader title={t("rc.title")} subtitle={t("rc.subtitle")} icon={HeartPulse} accent="recovery" />

      {snapshot.isError ? (
        <ErrorState onRetry={() => void snapshot.refetch()} />
      ) : !snapshot.data ? (
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-[22rem]" />
          <Skeleton className="h-36" />
          <Skeleton className="h-64" />
        </div>
      ) : (
        <div className="grid gap-4 desk:grid-cols-2 desk:items-start">
          <div className="contents desk:block desk:space-y-4">
            <div className="order-1">
              <VitalsCard snapshot={snapshot.data} />
            </div>
            <div className="order-2">
              <SleepCard snapshot={snapshot.data} openInitially={params.get("sheet") === "sleep"} />
            </div>
            <Card padded={false} className="order-5 p-2">
              <ActivityStrip
                levels={strip}
                accent="recovery"
                label={t("rc.history")}
                summary={tn("count.days", strip.filter((level) => level > 0).length)}
                onOpen={() => setCalendar(true)}
              />
            </Card>
          </div>
          <div className="contents desk:block desk:space-y-4">
            <div className="order-3">
              <HabitsCard snapshot={snapshot.data} />
            </div>
            <div className="order-4">
              <Tips tips={snapshot.data.recommendations?.items ?? []} />
            </div>
          </div>
        </div>
      )}

      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} accent="recovery" days={calendarDays} />
    </div>
  );
}
