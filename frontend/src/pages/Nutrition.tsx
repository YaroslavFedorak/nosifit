import { UtensilsCrossed } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { useNutritionDay, useNutritionHeatmap, useNutritionTips } from "../api/queries";
import type { MealCategory } from "../api/types";
import { ActivityStrip, STRIP_DAYS } from "../components/ui/ActivityStrip";
import { CalendarSheet, type CalendarDay } from "../components/ui/CalendarSheet";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { ErrorState, Skeleton } from "../components/ui/States";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { cn } from "../lib/cn";
import { addDays, isoDay, num } from "../lib/format";
import { useTitle } from "../lib/useTitle";
import { CalorieCard } from "./nutrition/CalorieCard";
import { MealsCard } from "./nutrition/MealsCard";
import { ProductSheet } from "./nutrition/ProductSheet";
import { QuickRow } from "./nutrition/QuickRow";

const TIP_LIMIT = 2;

/** The meal a user is most likely logging right now. */
function mealForNow(hour = new Date().getHours()): MealCategory {
  if (hour < 11) return "breakfast";
  if (hour < 16) return "lunch";
  if (hour < 21) return "dinner";
  return "snack";
}
const TIP_BAR = { high: "bg-danger", medium: "bg-warn", low: "bg-ok" } as const;

/** Nutrition tips, at most two at a time. */
function Tips() {
  const { t } = useT();
  const text = useServerText();
  const tips = useNutritionTips();
  const shown = (tips.data ?? [])
    .map((tip) => ({ tip, title: text.text(tip.title_key, tip.params), body: text.text(tip.message_key, tip.params) }))
    .filter((entry) => entry.title)
    .slice(0, TIP_LIMIT);
  if (shown.length === 0) return null;

  return (
    <Card aria-labelledby="tips-title">
      <h2 id="tips-title" className="text-base font-semibold">
        {t("nu.tips")}
      </h2>
      <ul className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-2.5">
        {shown.map(({ tip, title, body }) => (
          <li key={tip.type + tip.title_key} className="flex gap-3 rounded-xl border border-line bg-surface-2/50 p-3.5">
            <span
              className={cn("w-1 shrink-0 self-stretch rounded-full", TIP_BAR[tip.priority as keyof typeof TIP_BAR] ?? "bg-warn")}
              aria-hidden="true"
            />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold leading-snug">{title}</h3>
              {body && <p className="mt-1 text-sm text-fg-muted">{body}</p>}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export default function Nutrition() {
  const { t, tn } = useT();
  useTitle(t("nav.nutrition"));
  const [params] = useSearchParams();
  const day = useNutritionDay();
  const heatmap = useNutritionHeatmap();
  const [adding, setAdding] = useState<MealCategory | null>(params.get("sheet") === "add" ? mealForNow() : null);
  const [calendar, setCalendar] = useState(false);

  const { strip, calendarDays } = useMemo(() => {
    const days = heatmap.data ?? [];
    const level = (value: number): number => Math.min(4, Math.ceil(value * 0.8));
    const byDate = new Map(days.map((item) => [item.date, level(item.level)]));
    const last = new Date();
    return {
      strip: Array.from({ length: STRIP_DAYS }, (_, index) => byDate.get(isoDay(addDays(last, index - (STRIP_DAYS - 1)))) ?? 0),
      calendarDays: days.map<CalendarDay>((item) => ({
        date: item.date,
        level: level(item.level),
        note: item.kcal > 0 ? `${num(item.kcal, 0)} ${t("unit.kcal")}` : undefined,
      })),
    };
  }, [heatmap.data, t]);

  if (day.isError) return <ErrorState onRetry={() => void day.refetch()} />;

  return (
    <div data-accent="nutrition">
      <PageHeader title={t("nu.title")} subtitle={t("nu.subtitle")} icon={UtensilsCrossed} accent="nutrition" />

      {!day.data ? (
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-[26rem]" />
          <Skeleton className="h-44" />
        </div>
      ) : (
        <div className="grid gap-4 desk:grid-cols-2 desk:items-start">
          <div className="contents desk:block desk:space-y-4">
            <div className="order-1">
              <CalorieCard day={day.data} onAdd={() => setAdding(mealForNow())} />
            </div>
            <div className="order-3">
              <QuickRow />
            </div>
          </div>
          <div className="contents desk:block desk:space-y-4">
            <div className="order-2">
              <MealsCard day={day.data} onAdd={setAdding} />
            </div>
            <div className="order-4">
              <Tips />
            </div>
            <Card padded={false} className="order-5 p-2">
              <ActivityStrip
                levels={strip}
                accent="nutrition"
                label={t("nu.history")}
                summary={tn("count.days", strip.filter((level) => level > 0).length)}
                onOpen={() => setCalendar(true)}
              />
            </Card>
          </div>
        </div>
      )}

      {adding && <ProductSheet key={adding} open onClose={() => setAdding(null)} initialCategory={adding} />}
      <CalendarSheet open={calendar} onClose={() => setCalendar(false)} title={t("cal.title")} accent="nutrition" days={calendarDays} />
    </div>
  );
}
