import { ChevronDown, History } from "lucide-react";
import { useMemo, useState } from "react";
import { useTrainingDay, useTrainingHeatmap } from "../../api/queries";
import { ActivityStrip, STRIP_DAYS } from "../../components/ui/ActivityStrip";
import { CalendarSheet, type CalendarDay } from "../../components/ui/CalendarSheet";
import { Card } from "../../components/ui/Card";
import { Collapse } from "../../components/ui/Collapse";
import { EmptyState, ErrorState, Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { addDays, capitalize, dateText, isoDay, levelFromScore, num, parseDay } from "../../lib/format";

const PAGE = 5;

/** Hard sets are weighted by effort (14.6); the screen counts them as whole sets. */
const wholeSets = (value: number): number => Math.max(1, Math.round(value));

function DayRow({ date, hardSets }: { date: string; hardSets: number }) {
  const { t, tn, locale } = useT();
  const text = useServerText();
  const [open, setOpen] = useState(false);
  const day = useTrainingDay(date, open);
  const exercises = day.data?.sessions.flatMap((session) => session.exercises) ?? [];

  return (
    <li className="border-t border-line first:border-t-0">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-tap-lg w-full items-center justify-between gap-3 py-2 text-left"
      >
        <span>
          <span className="block text-sm font-semibold">
            {capitalize(dateText(locale, parseDay(date), { weekday: "short", day: "numeric", month: "long" }))}
          </span>
          <span className="block text-xs text-fg-muted">{tn("count.hardSets", wholeSets(hardSets))}</span>
        </span>
        <ChevronDown size={18} className={cn("shrink-0 text-fg-soft transition-transform", open && "rotate-180")} aria-hidden="true" />
      </button>
      <Collapse open={open}>
        {day.isPending ? (
          <Skeleton className="mb-3 h-16" />
        ) : (
          <ul className="space-y-2 pb-3">
            {exercises.map((exercise, index) => (
              <li key={index} className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0">{text.exercise(exercise.slug, exercise.name)}</span>
                <span className="shrink-0 tabular-nums text-fg-muted">
                  {exercise.sets} × {exercise.reps ?? exercise.duration_sec ?? "–"}
                  {exercise.load ? ` × ${num(exercise.load)} ${t("unit.kg")}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Collapse>
    </li>
  );
}

export function HistoryTab() {
  const { t, tn } = useT();
  const heatmap = useTrainingHeatmap();
  const [calendar, setCalendar] = useState(false);
  const [shown, setShown] = useState(PAGE);

  const { strip, worked, calendarDays } = useMemo(() => {
    const days = heatmap.data ?? [];
    const byDate = new Map(days.map((day) => [day.date, day]));
    const last = new Date();
    const levels = Array.from({ length: STRIP_DAYS }, (_, index) => {
      const day = byDate.get(isoDay(addDays(last, index - (STRIP_DAYS - 1))));
      return levelFromScore(day?.intensity_percent);
    });
    const cutoff = isoDay(addDays(last, -(STRIP_DAYS - 1)));
    return {
      strip: levels,
      worked: days.filter((day) => day.hard_sets > 0 && day.date >= cutoff).sort((a, b) => b.date.localeCompare(a.date)),
      calendarDays: days.map<CalendarDay>((day) => ({
        date: day.date,
        level: levelFromScore(day.intensity_percent),
        note: day.hard_sets > 0 ? tn("count.hardSets", wholeSets(day.hard_sets)) : undefined,
      })),
    };
  }, [heatmap.data, tn]);

  if (heatmap.isError) return <ErrorState onRetry={() => void heatmap.refetch()} />;
  if (heatmap.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-24" />
        <Skeleton className="h-56" />
      </div>
    );
  }

  return (
    <div className="grid gap-4 desk:grid-cols-[22rem_minmax(0,1fr)] desk:items-start">
      <Card padded={false} accent="training" className="p-2 pt-3">
        <ActivityStrip
          levels={strip}
          accent="training"
          label={t("dash.activity")}
          summary={tn("count.days", strip.filter((level) => level > 0).length)}
          onOpen={() => setCalendar(true)}
        />
      </Card>

      <Card aria-labelledby="recent-title">
        <h2 id="recent-title" className="text-base font-semibold">
          {t("tr.history.title")}
        </h2>
        {worked.length === 0 ? (
          <EmptyState icon={<History size={22} />} title={t("tr.history.empty")} />
        ) : (
          <>
            <ul className="mt-2">
              {worked.slice(0, shown).map((day) => (
                <DayRow key={day.date} date={day.date} hardSets={day.hard_sets} />
              ))}
            </ul>
            {worked.length > shown && (
              <button
                type="button"
                onClick={() => setShown((count) => count + PAGE)}
                className="mt-2 min-h-tap w-full rounded-xl text-sm font-semibold text-fg-muted transition hover:bg-white/5 hover:text-fg"
              >
                {t("common.showMore")}
              </button>
            )}
          </>
        )}
      </Card>

      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} accent="training" days={calendarDays} />
    </div>
  );
}
