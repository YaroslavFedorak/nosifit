import { CalendarDays, Moon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { useHabits, useRecoveryHeatmap, useRecoverySnapshot } from "../api/queries";
import type { RecoverySnapshot } from "../api/types";
import { Page } from "../app/Page";
import { useLog } from "../features/log/LogProvider";
import { HabitCatalogSheet, byCategory } from "../features/recovery/HabitCatalogSheet";
import { HabitList } from "../features/recovery/HabitList";
import { useT } from "../i18n";
import type { TKey } from "../i18n/en";
import { useServerText } from "../i18n/server";
import { isoDay, levelFromScore, parseDay, shortDay, splitMinutes, timeRange } from "../lib/format";
import { Button, IconButton } from "../ui/Button";
import { CalendarSheet, type CalendarDay } from "../ui/Calendar";
import { Progress } from "../ui/Chart";
import { Empty, ErrorNote, Skeleton } from "../ui/Feedback";
import { Group, Panel, Section } from "../ui/Layout";

const TIP_LIMIT = 2;

function levelKey(score: number | null): TKey {
  if (score == null) return "recovery.level.none";
  if (score >= 85) return "recovery.level.great";
  if (score >= 65) return "recovery.level.good";
  if (score >= 40) return "recovery.level.fair";
  return "recovery.level.low";
}

/** Last night in one figure, or a quiet invitation to record it. */
function SleepBlock({ snapshot }: { snapshot: RecoverySnapshot | null }) {
  const { t, locale } = useT();
  const log = useLog();
  const today = snapshot && snapshot.date === isoDay() && (snapshot.sleep_duration_minutes ?? 0) > 0 ? snapshot : null;
  const earlier = !today && snapshot && (snapshot.sleep_duration_minutes ?? 0) > 0 ? snapshot : null;

  if (!today) {
    return (
      <Panel>
        <h2 className="text-lg">{t("sleep.ask")}</h2>
        <p className="mt-1 text-sm text-muted">
          {earlier
            ? t("sleep.lastEntry", { date: shortDay(locale, parseDay(earlier.date)), ...splitMinutes(earlier.sleep_duration_minutes ?? 0) })
            : t("sleep.askText")}
        </p>
        <Button variant="primary" className="mt-4" icon={<Moon size={16} aria-hidden="true" />} onClick={() => log.open({ kind: "sleep" })}>
          {t("sleep.log")}
        </Button>
      </Panel>
    );
  }

  const { h, m } = splitMinutes(today.sleep_duration_minutes ?? 0);
  return (
    <Panel className="flex items-end justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-sm font-normal tracking-normal text-muted">{t("sleep.night")}</h2>
        <p className="mt-1">
          <span className="figure text-3xl">{h}</span>
          <span className="ml-1 mr-2 text-sm text-muted">{t("unit.h")}</span>
          <span className="figure text-3xl">{m}</span>
          <span className="ml-1 text-sm text-muted">{t("unit.min")}</span>
        </p>
        {today.sleep_start && today.sleep_end && (
          <p className="figure mt-1.5 text-sm font-normal text-ink-2">
            {timeRange(today.sleep_start, today.sleep_end)}
          </p>
        )}
      </div>
      <Button onClick={() => log.open({ kind: "sleep" })}>{t("common.edit")}</Button>
    </Panel>
  );
}

/** How recovered the body is, in a word first, and what the estimate is made of on request. */
function StateBlock({ snapshot }: { snapshot: RecoverySnapshot }) {
  const { t, locale } = useT();
  const score = snapshot.recovery_score;
  if (!score) return null;
  const parts: Array<{ label: TKey; value: number | null }> = [
    { label: "recovery.part.sleep", value: snapshot.sleep_score },
    { label: "recovery.part.load", value: snapshot.training_score },
    { label: "recovery.part.energy", value: snapshot.energy_score },
    { label: "recovery.part.habits", value: snapshot.habit_score },
  ];
  const measured = parts.filter((part) => part.value != null && part.value > 0);

  return (
    <Section title={t("recovery.state")} note={snapshot.date === isoDay() ? undefined : t("recovery.asOf", { date: shortDay(locale, parseDay(snapshot.date)) })}>
      <Panel>
        <p className="flex items-baseline justify-between gap-3">
          <span className="text-lg font-semibold tracking-[-0.01em]">{t(levelKey(score))}</span>
          <span className="figure text-sm font-normal text-muted">{t("recovery.scoreOf", { n: Math.round(score) })}</span>
        </p>
        <Progress value={score / 100} label={t("recovery.state")} tone="recovery" className="mt-3 h-2" />
        {measured.length > 0 && (
          <details className="group mt-3">
            <summary className="flex min-h-tap cursor-pointer list-none items-center text-sm font-medium text-ink-2 hover:text-ink [&::-webkit-details-marker]:hidden">
              {t("recovery.parts")}
            </summary>
            <ul className="space-y-3 pb-1 pt-1">
              {measured.map((part) => (
                <li key={part.label}>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span>{t(part.label)}</span>
                    <span className="text-muted">{t(levelKey(part.value))}</span>
                  </div>
                  <Progress value={(part.value ?? 0) / 100} label={t(part.label)} tone="recovery" className="mt-1.5" />
                </li>
              ))}
            </ul>
          </details>
        )}
      </Panel>
    </Section>
  );
}

function Tips({ snapshot }: { snapshot: RecoverySnapshot }) {
  const { t } = useT();
  const text = useServerText();
  const entries = (snapshot.recommendations?.items ?? [])
    .map((tip) => {
      const muscle = typeof tip.params.muscle === "string" ? text.muscle(tip.params.muscle).toLocaleLowerCase() : undefined;
      const params = muscle ? { ...tip.params, muscle } : tip.params;
      return { id: tip.id, title: text.text(tip.title_key, params), body: text.text(tip.message_key, params) };
    })
    .filter((entry) => entry.title)
    .slice(0, TIP_LIMIT);
  if (entries.length === 0) return null;
  return (
    <Section title={t("recovery.tips")}>
      <ul className="space-y-4">
        {entries.map((tip) => (
          <li key={tip.id}>
            <p className="font-medium">{tip.title}</p>
            {tip.body && <p className="mt-1 max-w-[56ch] text-sm text-ink-2">{tip.body}</p>}
          </li>
        ))}
      </ul>
    </Section>
  );
}

export default function Recovery() {
  const { t } = useT();
  const text = useServerText();
  const log = useLog();
  const [params, setParams] = useSearchParams();
  const snapshot = useRecoverySnapshot();
  const habits = useHabits();
  const [catalog, setCatalog] = useState(false);
  const [calendar, setCalendar] = useState(false);
  const heatmap = useRecoveryHeatmap(calendar);

  const sheet = params.get("sheet");
  useEffect(() => {
    if (sheet !== "sleep") return;
    log.open({ kind: "sleep" });
    const next = new URLSearchParams(params);
    next.delete("sheet");
    setParams(next, { replace: true });
    // Runs once for the link that carried the parameter.
  }, [sheet]);

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      (heatmap.data ?? []).map((day) => ({
        date: day.date,
        level: levelFromScore(day.recovery_score),
        note: day.recovery_score ? `${t(levelKey(day.recovery_score))}, ${t("recovery.scoreOf", { n: Math.round(day.recovery_score) })}` : undefined,
      })),
    [heatmap.data, t],
  );

  const list = habits.data ?? [];
  const done = list.filter((habit) => habit.completed).length;
  const groups = byCategory(list);

  return (
    <Page
      title={t("nav.recovery")}
      tone="recovery"
      action={
        <IconButton label={t("cal.open")} onClick={() => setCalendar(true)}>
          <CalendarDays size={20} />
        </IconButton>
      }
    >
      {habits.isError ? (
        <ErrorNote onRetry={() => void habits.refetch()} />
      ) : habits.isPending || snapshot.isPending ? (
        <div className="grid gap-6 desk:grid-cols-12" aria-busy="true">
          <Skeleton className="h-72 desk:col-span-7" />
          <Skeleton className="h-40 desk:col-span-5" />
        </div>
      ) : (
        <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start">
          <div className="contents desk:col-span-5 desk:col-start-8 desk:row-start-1 desk:block desk:space-y-8">
            <div className="order-1">
              <SleepBlock snapshot={snapshot.data ?? null} />
            </div>
            <div className="order-3 space-y-8 empty:hidden">
              {snapshot.data && <StateBlock snapshot={snapshot.data} />}
              {snapshot.data && <Tips snapshot={snapshot.data} />}
            </div>
          </div>

          <div className="order-2 desk:col-span-7 desk:col-start-1 desk:row-start-1">
            <Section
              title={t("habits.today")}
              note={list.length > 0 ? t("habits.count", { done, total: list.length }) : undefined}
              action={
                list.length > 0 ? (
                  <Button variant="quiet" onClick={() => setCatalog(true)}>
                    {t("habits.edit")}
                  </Button>
                ) : undefined
              }
            >
              {list.length === 0 ? (
                <Empty
                  title={t("habits.empty")}
                  text={t("habits.emptyText")}
                  action={
                    <Button variant="primary" onClick={() => setCatalog(true)}>
                      {t("habits.pick")}
                    </Button>
                  }
                />
              ) : (
                <div className="space-y-5">
                  {groups.map(([category, items]) => (
                    <div key={category}>
                      <h3 className="mb-1.5 text-sm font-normal tracking-normal text-muted">{text.habitCategory(category)}</h3>
                      <Group>
                        <HabitList habits={items} />
                      </Group>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </div>
        </div>
      )}

      {catalog && <HabitCatalogSheet mine={list} onClose={() => setCatalog(false)} />}
      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} tone="recovery" days={calendarDays} />
    </Page>
  );
}
