import { ChevronRight, Dumbbell, Flame, HeartPulse, Moon, Sparkles, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router";
import {
  useDashboardHeatmap,
  useDashboardRecommendation,
  useDashboardToday,
  useNutritionDay,
  useRecoverySnapshot,
  useTrainingSession,
} from "../api/queries";
import { entriesOf } from "../api/session";
import type { DashboardToday, NutritionDay, RecoverySnapshot } from "../api/types";
import { ActivityStrip, STRIP_DAYS } from "../components/ui/ActivityStrip";
import { Bar } from "../components/ui/Bar";
import { ButtonLink } from "../components/ui/Button";
import { CalendarSheet, type CalendarDay } from "../components/ui/CalendarSheet";
import { Card, cardClass, type Accent } from "../components/ui/Card";
import { Ring } from "../components/ui/Ring";
import { ErrorState, Skeleton } from "../components/ui/States";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { bootstrap } from "../lib/bootstrap";
import { cn } from "../lib/cn";
import { addDays, capitalize, dateText, isoDay, levelFromScore, num, ratio } from "../lib/format";
import { describeRecommendation } from "../lib/recommendations";
import { useTitle } from "../lib/useTitle";

type NextKey = "sleep" | "workout" | "meal" | "habits" | "ok";

interface NextStep {
  key: NextKey;
  to: string;
  accent: Accent;
  icon: LucideIcon;
  values?: Record<string, string | number>;
}

/** One thing to do next, picked from what is still missing today. */
function pickNext(today: DashboardToday, nutrition: NutritionDay | undefined, snapshot: RecoverySnapshot | undefined, hour: number): NextStep {
  const sleptMinutes = snapshot?.sleep_duration_minutes ?? 0;
  if (today.recovery.sleep_hours <= 0 && sleptMinutes <= 0 && hour < 15) {
    return { key: "sleep", to: "/recovery?sheet=sleep", accent: "recovery", icon: Moon };
  }
  if (!today.training.completed && today.training.exercise_count === 0) {
    return { key: "workout", to: "/training", accent: "training", icon: Dumbbell };
  }
  if (nutrition?.goals_available && nutrition.kcal_goal > 0 && hour >= 11 && nutrition.kcal / nutrition.kcal_goal < 0.2) {
    const pct = Math.round((nutrition.kcal / nutrition.kcal_goal) * 100);
    return { key: "meal", to: "/nutrition?sheet=add", accent: "nutrition", icon: UtensilsCrossed, values: { pct } };
  }
  const habits = snapshot?.habits ?? [];
  const done = habits.filter((habit) => habit.completed).length;
  if (habits.length > 0 && done < habits.length) {
    return { key: "habits", to: "/recovery", accent: "recovery", icon: HeartPulse, values: { done, total: habits.length } };
  }
  return { key: "ok", to: "/training", accent: "training", icon: Sparkles };
}

function StatChip({ to, accent, icon: Icon, value, label }: { to: string; accent: Accent; icon: LucideIcon; value: string; label: string }) {
  return (
    <Link
      to={to}
      data-accent={accent}
      className="flex min-h-tap flex-col gap-1 rounded-xl px-2 py-2 transition hover:bg-white/5 active:scale-[0.98]"
    >
      <span className="flex items-center gap-1.5">
        <Icon size={16} className="shrink-0 text-accent" aria-hidden="true" />
        <span className="text-lg font-semibold leading-tight tabular-nums">{value}</span>
      </span>
      <span className="text-xs text-fg-muted">{label}</span>
    </Link>
  );
}

/** A thin labelled bar for the previews inside the module cards. */
function MiniBar({ label, value, share, tone = "accent" }: { label: string; value: string; share: number; tone?: "accent" | "warn" }) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-fg-muted">{label}</span>
        <span className="tabular-nums text-fg-muted">{value}</span>
      </div>
      <Bar value={share} tone={tone} label={label} />
    </div>
  );
}

/**
 * A module at a glance. On phones it is one compact row; from tablet width,
 * where there is room, a small preview of the module sits under it.
 */
function ModuleCard({
  to,
  accent,
  icon: Icon,
  title,
  summary,
  preview,
}: {
  to: string;
  accent: Accent;
  icon: LucideIcon;
  title: string;
  summary: string;
  preview?: ReactNode;
}) {
  return (
    <Link
      to={to}
      data-accent={accent}
      className={cn(cardClass({ accent, padded: false, strip: true }), "flex flex-col px-4 py-3 transition hover:bg-surface-2 active:scale-[0.99]")}
    >
      <div className="flex min-h-12 items-center gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-accent-soft bg-accent-soft text-accent" aria-hidden="true">
          <Icon size={20} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-base font-semibold">{title}</span>
          <span className="block text-sm text-fg-muted">{summary}</span>
        </span>
        <ChevronRight size={18} className="shrink-0 text-fg-soft" aria-hidden="true" />
      </div>
      {preview && <div className="mt-3 hidden flex-1 space-y-2 border-t border-line pt-3 tab:block">{preview}</div>}
    </Link>
  );
}

export default function Dashboard() {
  const { t, tn, locale } = useT();
  const text = useServerText();
  useTitle(t("nav.dashboard"));

  const today = useDashboardToday();
  const nutrition = useNutritionDay();
  const snapshot = useRecoverySnapshot();
  const session = useTrainingSession();
  const heatmap = useDashboardHeatmap();
  const recommendation = useDashboardRecommendation();
  const [calendarOpen, setCalendarOpen] = useState(false);

  const strip = useMemo(() => {
    const levels = new Map((heatmap.data ?? []).map((day) => [day.date, levelFromScore(day.daily_score)]));
    const last = new Date();
    return Array.from({ length: STRIP_DAYS }, (_, index) => levels.get(isoDay(addDays(last, index - (STRIP_DAYS - 1)))) ?? 0);
  }, [heatmap.data]);

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      (heatmap.data ?? []).map((day) => ({
        date: day.date,
        level: levelFromScore(day.daily_score),
        note: day.daily_score != null ? `${t("dash.score")}: ${day.daily_score}` : undefined,
      })),
    [heatmap.data, t],
  );

  if (today.isError) return <ErrorState onRetry={() => void today.refetch()} />;
  if (!today.data) {
    return (
      <div className="grid gap-4 desk:grid-cols-12" aria-busy="true">
        <Skeleton className="h-[26rem] tab:h-72 desk:col-span-7" />
        <Skeleton className="h-52 tab:h-72 desk:col-span-5" />
        <Skeleton className="h-24 desk:col-span-12" />
      </div>
    );
  }

  const data = today.data;
  const day = nutrition.data;
  const score = Math.round(data.daily_score ?? 0);
  const remaining = day?.goals_available ? day.kcal_remaining : null;
  const sleepText = data.recovery.sleep_hours > 0 ? `${num(data.recovery.sleep_hours)}\u00a0${t("unit.h")}` : t("dash.sleep.none");
  const next = pickNext(data, day, snapshot.data, new Date().getHours());
  const tip = recommendation.data?.daily ? describeRecommendation(recommendation.data.daily, text) : null;
  const activeDays = strip.filter((level) => level > 0).length;

  const trainingSummary = session.data
    ? `${tn("count.exercises", session.data.totals.exercises)}, ${tn("count.sets", session.data.totals.sets)}`
    : data.training.exercise_count > 0
      ? tn("count.exercises", data.training.exercise_count)
      : t("dash.mod.training.empty");
  const nutritionSummary =
    remaining === null
      ? `${num(data.nutrition.calories, 0)} ${t("unit.kcal")}`
      : t(remaining >= 0 ? "dash.mod.nutrition" : "dash.mod.nutritionOver", {
          kcal: num(Math.abs(remaining), 0),
          water: num(data.nutrition.water),
        });
  const recoverySummary = t("dash.mod.recovery", { score: data.recovery.score ?? "–", sleep: sleepText });

  const trainingPreview = session.data?.exercises.length ? (
    <ul className="space-y-1.5 text-sm">
      {/* Four on a monitor; three on a tablet, so the dashboard still fits a landscape screen. */}
      {session.data.exercises.slice(0, 4).map((exercise, index) => (
        <li key={exercise.id} className={cn("flex items-baseline justify-between gap-3", index === 3 && "hidden desk:flex")}>
          <span className="min-w-0 truncate">{text.exercise(exercise.slug, exercise.name)}</span>
          <span className="shrink-0 text-xs tabular-nums text-fg-muted">{tn("count.sets", entriesOf(exercise).length)}</span>
        </li>
      ))}
    </ul>
  ) : undefined;
  const macro = (label: string, value: number, goal: number) => (
    <MiniBar
      key={label}
      label={label}
      value={`${num(value, 0)} / ${goal > 0 ? num(goal, 0) : "–"} ${t("unit.g")}`}
      share={ratio(value, goal)}
      tone={ratio(value, goal) > 1.1 ? "warn" : "accent"}
    />
  );
  const nutritionPreview = day ? (
    <>
      {macro(t("nu.protein"), day.protein, day.protein_goal)}
      {macro(t("nu.fat"), day.fat, day.fat_goal)}
      {macro(t("nu.carbs"), day.carb, day.carb_goal)}
    </>
  ) : undefined;
  const vital = (label: string, value: number | null) => (
    <MiniBar key={label} label={label} value={value == null ? "–" : `${Math.round(value)}%`} share={(value ?? 0) / 100} />
  );
  const recoveryPreview = snapshot.data ? (
    <>
      {vital(t("rc.vital.sleep"), snapshot.data.sleep_score)}
      {vital(t("rc.vital.energy"), snapshot.data.energy_score)}
      {vital(t("rc.vital.habits"), snapshot.data.habit_score)}
    </>
  ) : undefined;

  return (
    <div className="grid gap-4 desk:grid-cols-12">
      {/* Phone: stacked. Tablet and desktop: the ring on the left, the greeting and the figures beside it as
          one group, centred against the ring. */}
      <Card
        tone="hero"
        accent="training"
        aria-labelledby="today-title"
        className="tab:grid tab:grid-cols-[auto_minmax(0,1fr)] tab:grid-rows-[1fr_auto_auto_1fr] tab:gap-x-8 desk:col-span-7"
      >
        <div className="tab:col-start-2 tab:row-start-2">
          <p className="text-sm text-fg-muted">
            <time dateTime={isoDay()}>{capitalize(dateText(locale, new Date(), { weekday: "long", day: "numeric", month: "long" }))}</time>
          </p>
          <h1 id="today-title" className="mt-1 text-2xl font-semibold tracking-tight">
            {t("dash.greeting", { name: bootstrap.user?.name ?? "" })}
          </h1>
        </div>

        <div className="mt-6 flex justify-center tab:col-start-1 tab:row-span-4 tab:row-start-1 tab:mt-0 tab:items-center">
          <Ring
            value={score / 100}
            size={184}
            stroke={13}
            glow
            className="size-[184px] tab:size-40 desk:size-[184px]"
            label={t("dash.scoreLabel", { n: score })}
          >
            <div>
              <div className="text-5xl font-semibold leading-none tracking-tight tabular-nums">{score}</div>
              <div className="mt-1.5 text-xs font-medium text-fg-muted">{t("dash.score")}</div>
            </div>
          </Ring>
        </div>

        <div className="mt-6 border-t border-line pt-2 tab:col-start-2 tab:row-start-3 tab:mt-5">
          <div className="-mx-2 grid grid-cols-3 gap-1">
            <StatChip
              to="/training"
              accent="training"
              icon={Dumbbell}
              value={data.training.completed ? t("dash.workout.done") : t("dash.workout.todo")}
              label={t("dash.chip.workout")}
            />
            <StatChip
              to="/nutrition"
              accent="nutrition"
              icon={Flame}
              value={remaining === null ? "–" : num(Math.abs(remaining), 0)}
              label={remaining !== null && remaining < 0 ? t("dash.chip.kcalOver") : t("dash.chip.kcal")}
            />
            <StatChip to="/recovery" accent="recovery" icon={Moon} value={sleepText} label={t("dash.chip.sleep")} />
          </div>
        </div>
      </Card>

      {/* The one thing to do next. On a tablet the action sits beside the text, so the page stays short. */}
      <Card
        tone="glass"
        accent={next.accent}
        strip
        aria-labelledby="next-title"
        className="flex flex-col tab:grid tab:grid-cols-[minmax(0,1fr)_15rem] tab:items-center tab:gap-x-6 desk:col-span-5 desk:flex desk:items-stretch"
      >
        <div className={cn(next.key === "ok" && "tab:col-span-2")}>
          <h2 id="next-title" className="text-lg font-semibold leading-snug">
            {t(`next.${next.key}.title` as "next.ok.title")}
          </h2>
          <p className="mt-1 text-sm text-fg-muted">{t(`next.${next.key}.text` as "next.ok.text", next.values)}</p>
        </div>
        {next.key !== "ok" && (
          <div className="mt-4 tab:mt-0 desk:mt-auto desk:pt-4">
            <ButtonLink to={next.to} variant="primary" size="lg" block icon={<next.icon size={18} aria-hidden="true" />}>
              {t(`next.${next.key}.cta` as "next.sleep.cta")}
            </ButtonLink>
          </div>
        )}
        {/* The tip: two lines on a phone, one sentence where the card is wide. */}
        {tip?.title && (
          <p className="mt-4 border-t border-line pt-3 text-sm text-fg-muted tab:col-span-2">
            <span className="font-medium text-fg">{t("next.tip")}:</span> {tip.title}
            {tip.body && (
              <span className="mt-0.5 block tab:mt-0 tab:inline">
                <span className="hidden tab:inline">. </span>
                {tip.body}
              </span>
            )}
          </p>
        )}
      </Card>

      <section aria-label={t("dash.modules")} className="grid gap-2 tab:grid-cols-3 tab:gap-3 desk:col-span-12 desk:gap-4">
        <ModuleCard to="/training" accent="training" icon={Dumbbell} title={t("nav.training")} summary={trainingSummary} preview={trainingPreview} />
        <ModuleCard
          to="/nutrition"
          accent="nutrition"
          icon={UtensilsCrossed}
          title={t("nav.nutrition")}
          summary={nutritionSummary}
          preview={nutritionPreview}
        />
        <ModuleCard to="/recovery" accent="recovery" icon={HeartPulse} title={t("nav.recovery")} summary={recoverySummary} preview={recoveryPreview} />
      </section>

      <Card padded={false} className="p-2 desk:col-span-12">
        <ActivityStrip
          levels={strip}
          accent="training"
          label={t("dash.activity")}
          summary={tn("count.days", activeDays)}
          onOpen={() => setCalendarOpen(true)}
        />
      </Card>

      <CalendarSheet open={calendarOpen} onClose={() => setCalendarOpen(false)} title={t("cal.title")} accent="training" days={calendarDays} />
    </div>
  );
}
