import { CalendarDays, ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";
import { useTrainingDay, useTrainingHeatmap, useWeeklySets } from "../../api/queries";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { addDays, isoDay, levelFromScore, longDay, num, parseDay, ratio, shortDay } from "../../lib/format";
import { Button } from "../../ui/Button";
import { CalendarSheet, type CalendarDay } from "../../ui/Calendar";
import { Progress } from "../../ui/Chart";
import { Empty, ErrorNote, Skeleton, SkeletonRows } from "../../ui/Feedback";
import { Group, Section, Stat } from "../../ui/Layout";

const PAGE = 6;
const RECENT_DAYS = 60;

/** The model weighs sets by effort ("14.6"); the screen counts them as whole sets. */
const wholeSets = (value: number): number => Math.max(1, Math.round(value));

function DayRow({ date, hardSets }: { date: string; hardSets: number }) {
  const { t, tn, locale } = useT();
  const text = useServerText();
  const [open, setOpen] = useState(false);
  const day = useTrainingDay(date, open);
  const exercises = day.data?.sessions.flatMap((session) => session.exercises) ?? [];

  return (
    <details className="group" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="flex min-h-[3.25rem] cursor-pointer list-none items-center gap-3 px-4 py-2 transition-colors duration-150 hover:bg-paper-3 [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">
          <span className="block font-medium">{longDay(locale, parseDay(date))}</span>
          <span className="block text-sm text-muted">{tn("count.sets", wholeSets(hardSets))}</span>
        </span>
        <ChevronDown size={18} className="text-muted transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="px-4 pb-3">
        {day.isPending ? (
          <SkeletonRows rows={2} />
        ) : (
          <ul className="divide-y divide-rule border-t border-rule">
            {exercises.map((exercise, index) => (
              <li key={index} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0 text-ink-2">{text.exercise(exercise.slug, exercise.name)}</span>
                <span className="figure shrink-0 font-normal text-muted">
                  {exercise.sets} × {exercise.reps ?? (exercise.duration_sec ? `${exercise.duration_sec} ${t("unit.s")}` : "–")}
                  {exercise.load ? ` × ${num(exercise.load)} ${t("unit.kg")}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

/** How the week's sets are spread over the muscle groups, the ones furthest from their target first. */
function WeeklyLoad() {
  const { t } = useT();
  const text = useServerText();
  const weekly = useWeeklySets();
  const [all, setAll] = useState(false);
  const sorted = useMemo(
    () => [...(weekly.data ?? [])].filter((item) => item.target_sets > 0).sort((a, b) => ratio(a.sets, a.target_sets) - ratio(b.sets, b.target_sets)),
    [weekly.data],
  );
  if (weekly.isPending || sorted.length === 0 || sorted.every((item) => item.sets <= 0)) return null;
  const shown = all ? sorted : sorted.slice(0, 4);

  return (
    <Section
      title={t("history.load")}
      note={t("history.loadNote")}
      tone="training"
      action={
        sorted.length > 4 ? (
          <Button variant="quiet" aria-expanded={all} onClick={() => setAll((value) => !value)}>
            {all ? t("common.showLess") : t("common.all", { n: sorted.length })}
          </Button>
        ) : undefined
      }
    >
      <ul className="space-y-3 rounded-card bg-paper-2 p-4">
        {shown.map((item) => {
          const name = text.muscle(item.muscle);
          const sets = Math.round(item.sets);
          const target = Math.max(1, Math.round(item.target_sets));
          return (
            <li key={item.muscle}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="font-medium">{name}</span>
                <span className="figure font-normal text-muted">{t("history.setsOf", { sets, target })}</span>
              </div>
              <Progress value={ratio(item.sets, item.target_sets)} label={name} tone={sets >= target ? "success" : "training"} className="mt-1.5" />
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

/** Past workouts, newest first, and the week's totals. */
export function HistoryTab() {
  const { t, tn, locale } = useT();
  const heatmap = useTrainingHeatmap();
  const [calendar, setCalendar] = useState(false);
  const [shown, setShown] = useState(PAGE);

  const { worked, week, calendarDays } = useMemo(() => {
    const days = heatmap.data ?? [];
    const today = new Date();
    const todayIso = isoDay(today);
    const cutoff = isoDay(addDays(today, -RECENT_DAYS));
    const monday = isoDay(addDays(today, -((today.getDay() + 6) % 7)));
    const done = days.filter((day) => day.hard_sets > 0 && day.date <= todayIso);
    const thisWeek = done.filter((day) => day.date >= monday);
    return {
      worked: done.filter((day) => day.date >= cutoff).sort((a, b) => b.date.localeCompare(a.date)),
      week: { workouts: thisWeek.length, sets: thisWeek.reduce((sum, day) => sum + wholeSets(day.hard_sets), 0) },
      calendarDays: days.map<CalendarDay>((day) => ({
        date: day.date,
        level: levelFromScore(day.intensity_percent),
        note: day.hard_sets > 0 ? tn("count.sets", wholeSets(day.hard_sets)) : undefined,
      })),
    };
  }, [heatmap.data, tn]);

  if (heatmap.isError) return <ErrorNote onRetry={() => void heatmap.refetch()} />;
  if (heatmap.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-16" />
        <Skeleton className="h-56" />
      </div>
    );
  }

  if (worked.length === 0) {
    return <Empty title={t("history.empty")} text={t("history.emptyText")} />;
  }

  const last = worked[0];

  return (
    <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start" data-tone="training">
      <div className="space-y-6 desk:col-span-7">
        <div className="grid grid-cols-3 gap-4">
          <Stat value={week.workouts > 0 ? week.workouts : "–"} label={t("history.weekWorkouts")} />
          <Stat value={week.sets > 0 ? week.sets : "–"} label={t("history.weekSets")} />
          {last && <Stat value={shortDay(locale, parseDay(last.date))} label={t("history.last")} className="[&>p:first-child]:text-lg" />}
        </div>
        <Section
          title={t("history.title")}
          action={
            <Button variant="quiet" icon={<CalendarDays size={16} aria-hidden="true" />} onClick={() => setCalendar(true)}>
              {t("week.calendar")}
            </Button>
          }
        >
          <Group>
            {worked.slice(0, shown).map((day) => (
              <DayRow key={day.date} date={day.date} hardSets={day.hard_sets} />
            ))}
          </Group>
          {worked.length > shown && (
            <Button variant="quiet" block className="mt-2" onClick={() => setShown((count) => count + PAGE)}>
              {t("common.showMore")}
            </Button>
          )}
        </Section>
      </div>
      <div className="desk:col-span-5">
        <WeeklyLoad />
      </div>
      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} tone="training" days={calendarDays} />
    </div>
  );
}
