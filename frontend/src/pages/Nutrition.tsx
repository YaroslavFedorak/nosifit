import { CalendarDays, ChevronLeft, ChevronRight, Copy, ScanBarcode, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { useCopyYesterday } from "../api/mutations";
import { useDiaryDay, useNutritionHeatmap, useNutritionTips, useWeight } from "../api/queries";
import type { MealCategory } from "../api/types";
import { Page } from "../app/Page";
import { useLog } from "../features/log/LogProvider";
import { DaySummary } from "../features/nutrition/DaySummary";
import { MealList } from "../features/nutrition/MealList";
import { WaterQuick } from "../features/nutrition/WaterQuick";
import { WeekIntake } from "../features/nutrition/WeekIntake";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { addDays, isoDay, longDay, num, parseDay } from "../lib/format";
import { Button, IconButton } from "../ui/Button";
import { CalendarSheet, type CalendarDay } from "../ui/Calendar";
import { ErrorNote, Skeleton } from "../ui/Feedback";
import { Section } from "../ui/Layout";

const TIP_LIMIT = 2;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** At most two of today's nutrition tips, said plainly. */
function Tips() {
  const { t } = useT();
  const text = useServerText();
  const tips = useNutritionTips();
  const shown = (tips.data ?? [])
    // "Nothing logged yet" is already what the empty diary says.
    .filter((tip) => tip.type !== "empty")
    .map((tip) => ({ key: tip.type + tip.title_key, title: text.text(tip.title_key, tip.params), body: text.text(tip.message_key, tip.params) }))
    .filter((entry) => entry.title)
    .slice(0, TIP_LIMIT);
  if (shown.length === 0) return null;

  return (
    <Section title={t("food.tips")}>
      <ul className="space-y-4">
        {shown.map((tip) => (
          <li key={tip.key}>
            <p className="font-medium">{tip.title}</p>
            {tip.body && <p className="mt-1 max-w-[56ch] text-sm text-ink-2">{tip.body}</p>}
          </li>
        ))}
      </ul>
    </Section>
  );
}

export default function Nutrition() {
  const { t, locale } = useT();
  const log = useLog();
  const [params, setParams] = useSearchParams();
  const today = isoDay();
  const requested = params.get("date");
  const date = requested && DATE_RE.test(requested) && requested <= today ? requested : today;
  const isToday = date === today;

  const day = useDiaryDay(date);
  const weight = useWeight();
  const copy = useCopyYesterday();
  const [calendar, setCalendar] = useState(false);
  const heatmap = useNutritionHeatmap(calendar);

  // Links from other screens may ask for the picker or the scanner straight away.
  const sheet = params.get("sheet");
  useEffect(() => {
    if (sheet !== "add" && sheet !== "scan") return;
    log.open({ kind: "food", scan: sheet === "scan" });
    const next = new URLSearchParams(params);
    next.delete("sheet");
    setParams(next, { replace: true });
    // Runs once for the link that carried the parameter.
  }, [sheet]);

  const goTo = (next: string) => setParams(next === today ? {} : { date: next }, { replace: true });
  const add = (category?: MealCategory, scan = false) => log.open({ kind: "food", category, date: isToday ? undefined : date, scan });

  const calendarDays = useMemo<CalendarDay[]>(
    () =>
      (heatmap.data ?? []).map((item) => ({
        date: item.date,
        level: Math.min(4, Math.ceil(item.level * 0.8)),
        note: item.kcal > 0 ? `${num(item.kcal, 0)} ${t("unit.kcal")}` : undefined,
      })),
    [heatmap.data, t],
  );

  const data = day.data;
  const empty = data ? data.meals.every((meal) => meal.items.length === 0) : false;

  return (
    <Page title={t("nav.nutrition")} tone="nutrition">
      <div className="mb-4 flex items-center gap-1">
        <IconButton label={t("food.day.prev")} onClick={() => goTo(isoDay(addDays(parseDay(date), -1)))}>
          <ChevronLeft size={20} />
        </IconButton>
        <p className="min-w-0 flex-1 truncate text-center font-medium tab:flex-none tab:px-2" aria-live="polite">
          {isToday ? t("food.day.today") : longDay(locale, parseDay(date))}
        </p>
        <IconButton label={t("food.day.next")} disabled={isToday} onClick={() => goTo(isoDay(addDays(parseDay(date), 1)))}>
          <ChevronRight size={20} />
        </IconButton>
        <IconButton label={t("cal.open")} className="tab:ml-auto" onClick={() => setCalendar(true)}>
          <CalendarDays size={20} />
        </IconButton>
      </div>

      {day.isError ? (
        <ErrorNote onRetry={() => void day.refetch()} />
      ) : !data ? (
        <div className="grid gap-6 desk:grid-cols-12" aria-busy="true">
          <Skeleton className="h-64 desk:col-span-7" />
          <Skeleton className="h-40 desk:col-span-5" />
        </div>
      ) : (
        <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start">
          <div className="contents desk:col-span-5 desk:col-start-8 desk:row-start-1 desk:block desk:space-y-8">
            <DaySummary day={data} className="order-1" />
            <div className="order-3 space-y-4 rounded-card bg-paper-2 p-4">
              <WaterQuick date={date} />
              {isToday && (
                <div className="flex items-center justify-between gap-3 border-t border-rule pt-4">
                  <div>
                    <p className="font-medium">{t("weight.title")}</p>
                    <p className="figure mt-0.5 text-sm font-normal text-ink-2">
                      {weight.data?.weight ? `${num(weight.data.weight)} ${t("unit.kg")}` : t("weight.none")}
                    </p>
                  </div>
                  <Button onClick={() => log.open({ kind: "weight" })}>{weight.data?.weight ? t("weight.update") : t("weight.add")}</Button>
                </div>
              )}
            </div>
            <div className="order-4 space-y-8 empty:hidden">
              <WeekIntake onPick={goTo} />
              {isToday && !empty && <Tips />}
            </div>
          </div>

          <div className="order-2 space-y-3 desk:col-span-7 desk:col-start-1 desk:row-start-1">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => add()}
                className="press flex min-h-control-lg min-w-0 flex-1 items-center gap-3 rounded-control border border-edge px-3 text-left text-muted hover:bg-paper-2"
              >
                <Search size={18} aria-hidden="true" />
                <span className="truncate">{t("food.search")}</span>
              </button>
              <IconButton tonal label={t("scan.title")} className="size-control-lg" onClick={() => add(undefined, true)}>
                <ScanBarcode size={20} />
              </IconButton>
            </div>
            <MealList day={data} onAdd={(category) => add(category)} />
            {isToday && empty && data.kcalYesterday > 0 && (
              <Button variant="quiet" icon={<Copy size={16} aria-hidden="true" />} busy={copy.isPending} onClick={() => copy.mutate()}>
                {t("food.copyYesterday", { kcal: num(data.kcalYesterday, 0) })}
              </Button>
            )}
          </div>
        </div>
      )}

      <CalendarSheet
        open={calendar}
        onClose={() => setCalendar(false)}
        title={t("cal.title")}
        tone="nutrition"
        days={calendarDays}
        detail={(picked) => {
          const info = calendarDays.find((item) => item.date === picked);
          return (
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-muted">{info?.note ?? t("cal.none")}</p>
              <Button
                onClick={() => {
                  goTo(picked);
                  setCalendar(false);
                }}
              >
                {t("food.day.open")}
              </Button>
            </div>
          );
        }}
      />
    </Page>
  );
}
