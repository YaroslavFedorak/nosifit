import { CalendarDays, ChevronRight, Dumbbell, Moon, Plus, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router";
import {
  useDashboardHeatmap,
  useDashboardRecommendation,
  useDiaryDay,
  useHabits,
  useNutritionStats,
  useRecoverySnapshot,
  useTrainingHeatmap,
  useTrainingSession,
  useTrainingToday,
  useWater,
  useWeight,
} from "../api/queries";
import { Page } from "../app/Page";
import type { Tone } from "../design/tokens";
import { dayState, greetingFor, nextStep, type DayState, type NextStep } from "../domain/day";
import { mealForNow } from "../domain/nutrition";
import { useLog } from "../features/log/LogProvider";
import { WaterQuick } from "../features/nutrition/WaterQuick";
import { HabitList } from "../features/recovery/HabitList";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { bootstrap } from "../lib/bootstrap";
import { addDays, isoDay, levelFromScore, longDay, num, ratio, splitMinutes, timeRange, weekdayLetter } from "../lib/format";
import { describeRecommendation } from "../lib/recommendations";
import { Button, ButtonLink, IconButton, buttonClass } from "../ui/Button";
import { CalendarSheet, type CalendarDay } from "../ui/Calendar";
import { Bars, Progress, type BarDatum } from "../ui/Chart";
import { ErrorNote, Skeleton } from "../ui/Feedback";
import { Group, Section } from "../ui/Layout";

const HABITS_SHOWN = 5;
const WEEK = 7;

function Glyph({ icon: Icon, tone }: { icon: LucideIcon; tone: Tone }) {
  return (
    <span data-tone={tone} className="text-tone" aria-hidden="true">
      <Icon size={20} />
    </span>
  );
}

/** The one thing worth doing now, said as a person would ask it. */
function NextStepBlock({ step, fresh }: { step: NextStep; fresh: boolean }) {
  const { t } = useT();
  const log = useLog();

  let title: string;
  let text: string;
  let action: ReactNode = null;

  switch (step.kind) {
    case "sleep":
      title = t("next.sleep.title");
      text = t("next.sleep.text");
      action = (
        <Button variant="primary" size="lg" icon={<Moon size={18} aria-hidden="true" />} onClick={() => log.open({ kind: "sleep" })}>
          {t("next.sleep.cta")}
        </Button>
      );
      break;
    case "meal":
      title = t(`next.meal.${step.meal}`);
      text = t("next.meal.text");
      action = (
        <Button variant="primary" size="lg" icon={<Plus size={18} aria-hidden="true" />} onClick={() => log.open({ kind: "food", category: step.meal })}>
          {t("next.meal.cta")}
        </Button>
      );
      break;
    case "workout":
      title = t("next.workout.title");
      text = t("next.workout.text", { n: step.exercises });
      action = (
        <ButtonLink to="/training" variant="primary" size="lg" icon={<Dumbbell size={18} aria-hidden="true" />}>
          {t("next.workout.cta")}
        </ButtonLink>
      );
      break;
    case "habits":
      title = t("next.habits.title");
      text = t("next.habits.text", { n: step.left });
      break;
    case "start":
      title = fresh ? t("next.start.title") : t("next.open.title");
      text = fresh ? t("next.start.text") : t("next.open.text");
      action = (
        <Button variant="primary" size="lg" icon={<Plus size={18} aria-hidden="true" />} onClick={() => log.open({ kind: "menu" })}>
          {t("log.add")}
        </Button>
      );
      break;
    default:
      title = t("next.done.title");
      text = t("next.done.text");
  }

  return (
    <section aria-labelledby="next-title" className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div className="min-w-0">
        <h2 id="next-title" className="text-xl desk:text-2xl">
          {title}
        </h2>
        <p className="mt-1.5 max-w-[46ch] text-ink-2">{text}</p>
      </div>
      {action}
    </section>
  );
}

/** What is recorded today, each line leading to its module. Nothing appears here before it is recorded. */
function TodayLog({ state }: { state: DayState }) {
  const { t, tn } = useT();
  const log = useLog();
  const rowClass = "flex min-h-[3.25rem] min-w-0 flex-1 items-center gap-3 px-4 py-2.5 transition-colors duration-150 hover:bg-paper-3";

  return (
    <Group>
      {state.food && (
        <div className="flex items-center" data-tone="nutrition">
          <Link to="/nutrition" className={rowClass}>
            <Glyph icon={UtensilsCrossed} tone="nutrition" />
            <span className="min-w-0 flex-1">
              <span className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{t("nav.nutrition")}</span>
                <span className="figure text-sm font-normal text-ink-2">
                  {state.food.goal ? t("food.kcalOf", { n: num(state.food.kcal, 0), goal: num(state.food.goal, 0) }) : `${num(state.food.kcal, 0)} ${t("unit.kcal")}`}
                </span>
              </span>
              {state.food.goal ? <Progress value={ratio(state.food.kcal, state.food.goal)} label={t("nav.nutrition")} className="mt-2" /> : null}
            </span>
          </Link>
          <IconButton tonal label={t("next.meal.cta")} className="mr-2" onClick={() => log.open({ kind: "food", category: mealForNow() })}>
            <Plus size={18} />
          </IconButton>
        </div>
      )}
      <div className="px-4 py-3">
        <WaterQuick />
      </div>
      {state.sleep && (
        <Link to="/recovery" className={rowClass}>
          <Glyph icon={Moon} tone="recovery" />
          <span className="min-w-0 flex-1 font-medium">{t("sleep.short")}</span>
          <span className="text-right text-sm text-ink-2">
            <span className="figure block font-normal">{t("sleep.duration", splitMinutes(state.sleep.minutes))}</span>
            {state.sleep.start && state.sleep.end && (
              <span className="figure block font-normal text-muted">
                {timeRange(state.sleep.start, state.sleep.end)}
              </span>
            )}
          </span>
          <ChevronRight size={18} className="text-muted" aria-hidden="true" />
        </Link>
      )}
      {state.workout ? (
        <Link to="/training" className={rowClass}>
          <Glyph icon={Dumbbell} tone="training" />
          <span className="min-w-0 flex-1 font-medium">{t("nav.training")}</span>
          <span className="text-right text-sm text-ink-2">
            {tn("count.exercises", state.workout.exercises)}, {tn("count.sets", state.workout.sets)}
          </span>
          <ChevronRight size={18} className="text-muted" aria-hidden="true" />
        </Link>
      ) : state.planned.length > 0 ? (
        <Link to="/training" className={rowClass}>
          <Glyph icon={Dumbbell} tone="training" />
          <span className="min-w-0 flex-1">
            <span className="block font-medium">{t("today.planned")}</span>
            <span className="block text-sm text-muted">{tn("count.exercises", state.planned.length)}</span>
          </span>
          <ChevronRight size={18} className="text-muted" aria-hidden="true" />
        </Link>
      ) : null}
    </Group>
  );
}

/** The areas with nothing recorded today, as quiet offers: names, not zeros. */
function MoreToLog({ state, weight }: { state: DayState; weight: number | null }) {
  const { t } = useT();
  const log = useLog();
  const chip = buttonClass({ variant: "secondary" });
  const offers: ReactNode[] = [];
  if (!state.food) {
    offers.push(
      <button key="food" type="button" className={chip} onClick={() => log.open({ kind: "food", category: mealForNow() })}>
        <UtensilsCrossed size={16} aria-hidden="true" /> {t("log.food")}
      </button>,
    );
  }
  if (!state.sleep) {
    offers.push(
      <button key="sleep" type="button" className={chip} onClick={() => log.open({ kind: "sleep" })}>
        <Moon size={16} aria-hidden="true" /> {t("sleep.short")}
      </button>,
    );
  }
  if (!state.workout && state.planned.length === 0) {
    offers.push(
      <Link key="workout" to="/training?sheet=exercise" className={chip}>
        <Dumbbell size={16} aria-hidden="true" /> {t("log.workout")}
      </Link>,
    );
  }
  offers.push(
    <button key="weight" type="button" className={chip} onClick={() => log.open({ kind: "weight" })}>
      {weight ? t("today.weightValue", { n: num(weight) }) : t("log.weight")}
    </button>,
  );
  return <div className="flex flex-wrap gap-2">{offers}</div>;
}

export default function Dashboard() {
  const { t, tn, locale } = useT();
  const text = useServerText();
  const now = new Date();

  const diary = useDiaryDay();
  const water = useWater();
  const snapshot = useRecoverySnapshot();
  const habits = useHabits();
  const session = useTrainingSession();
  const planToday = useTrainingToday();
  const heatmap = useDashboardHeatmap();
  const recommendation = useDashboardRecommendation();
  const stats = useNutritionStats(WEEK);
  const trainingDays = useTrainingHeatmap();
  const weight = useWeight();
  const [calendar, setCalendar] = useState(false);

  const week = useMemo(() => {
    const byDate = new Map((heatmap.data ?? []).map((day) => [day.date, day.daily_score ?? 0]));
    const bars: BarDatum[] = Array.from({ length: WEEK }, (_, index) => {
      const date = addDays(now, index - (WEEK - 1));
      const key = isoDay(date);
      const score = byDate.get(key) ?? 0;
      return {
        key,
        label: weekdayLetter(locale, date),
        value: score > 0 ? score : null,
        title: `${longDay(locale, date)}: ${score > 0 ? t("week.score", { n: Math.round(score) }) : t("cal.none")}`,
        current: index === WEEK - 1,
      };
    });
    const cutoff = isoDay(addDays(now, -(WEEK - 1)));
    const workouts = (trainingDays.data ?? []).filter((day) => day.hard_sets > 0 && day.date >= cutoff && day.date <= isoDay(now)).length;
    return { bars, workouts, active: bars.filter((bar) => bar.value !== null).length };
    // `now` is a new object on every render; the data decides when to recompute.
  }, [heatmap.data, trainingDays.data, locale, t]);

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      (heatmap.data ?? []).map((day) => ({
        date: day.date,
        level: levelFromScore(day.daily_score),
        note: day.daily_score ? t("week.score", { n: Math.round(day.daily_score) }) : undefined,
      })),
    [heatmap.data, t],
  );

  const loading = diary.isPending || habits.isPending || session.isPending || snapshot.isPending;
  const failed = diary.isError && habits.isError && session.isError;

  const state = dayState({
    diary: diary.data,
    water: water.data,
    snapshot: snapshot.data,
    habits: habits.data,
    session: session.data,
    planned: planToday.data?.plan.length ? planToday.data.exercises : [],
  });
  // An account with nothing on record yet: no history, no habits picked, nothing today.
  const fresh = !heatmap.isPending && (heatmap.data ?? []).every((day) => !day.daily_score) && state.habits.total === 0;
  const step = nextStep(state, now.getHours(), fresh);
  const list = habits.data ?? [];
  const tip = recommendation.data?.daily ? describeRecommendation(recommendation.data.daily, text) : null;
  const name = bootstrap.user?.name ?? "";

  return (
    <Page title={longDay(locale, now)} subtitle={t(`greeting.${greetingFor(now.getHours())}`, { name })}>
      {failed ? (
        <ErrorNote onRetry={() => void diary.refetch()} />
      ) : loading ? (
        <div className="grid gap-6 desk:grid-cols-12" aria-busy="true">
          <div className="space-y-4 desk:col-span-7">
            <Skeleton className="h-20" />
            <Skeleton className="h-44" />
          </div>
          <Skeleton className="h-56 desk:col-span-5" />
        </div>
      ) : (
        <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start">
          <div className="space-y-8 desk:col-span-7">
            <NextStepBlock step={step} fresh={fresh} />

            <Section title={t("today.title")}>
              <TodayLog state={state} />
              <div className="mt-3">
                <MoreToLog state={state} weight={weight.data?.weight ?? null} />
              </div>
            </Section>

            {list.length > 0 && (
              <Section
                title={t("habits.title")}
                note={t("habits.count", { done: state.habits.done, total: state.habits.total })}
                action={
                  list.length > HABITS_SHOWN ? (
                    <ButtonLink to="/recovery" variant="quiet">
                      {t("common.all", { n: list.length })}
                    </ButtonLink>
                  ) : undefined
                }
              >
                <Group>
                  <HabitList habits={list.slice(0, HABITS_SHOWN)} />
                </Group>
              </Section>
            )}
          </div>

          <div className="space-y-8 desk:col-span-5">
            {week.active > 0 && (
              <Section
                title={t("week.title")}
                tone="training"
                action={
                  <Button variant="quiet" icon={<CalendarDays size={16} aria-hidden="true" />} onClick={() => setCalendar(true)}>
                    {t("week.calendar")}
                  </Button>
                }
              >
                <div className="rounded-card bg-paper-2 p-4">
                  <Bars data={week.bars} label={t("week.title")} tone="training" />
                  <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-rule pt-4">
                    <div>
                      <dd className="figure text-lg">{tn("count.days", week.active)}</dd>
                      <dt className="mt-0.5 text-sm text-muted">{t("week.active")}</dt>
                    </div>
                    {week.workouts > 0 ? (
                      <div>
                        <dd className="figure text-lg">{tn("count.workouts", week.workouts)}</dd>
                        <dt className="mt-0.5 text-sm text-muted">{t("week.workouts")}</dt>
                      </div>
                    ) : stats.data?.avg_kcal ? (
                      <div>
                        <dd className="figure text-lg">
                          {num(stats.data.avg_kcal, 0)} {t("unit.kcal")}
                        </dd>
                        <dt className="mt-0.5 text-sm text-muted">{t("week.avgKcal")}</dt>
                      </div>
                    ) : null}
                  </dl>
                </div>
              </Section>
            )}

            {tip?.title && !fresh && (
              <Section title={t("today.tip")}>
                <p className="font-medium">{tip.title}</p>
                {tip.body && <p className="mt-1 max-w-[52ch] text-sm text-ink-2">{tip.body}</p>}
              </Section>
            )}
          </div>
        </div>
      )}

      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} tone="training" days={calendarDays} />
    </Page>
  );
}
