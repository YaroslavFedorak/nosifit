import { useNutritionStats } from "../../api/queries";
import { useT } from "../../i18n";
import type { TKey } from "../../i18n/en";
import { addDays, isoDay, longDay, num, weekdayLetter } from "../../lib/format";
import { Bars, Sparkline, type BarDatum } from "../../ui/Chart";
import { Section } from "../../ui/Layout";

const DAYS = 7;

const TREND: Record<string, TKey> = {
  stable: "weight.trend.stable",
  increasing: "weight.trend.up",
  decreasing: "weight.trend.down",
};

/**
 * Energy over the last seven days against the target, and where the weight
 * is heading. Shown once there are at least two logged days to compare.
 */
export function WeekIntake({ onPick }: { onPick: (date: string) => void }) {
  const { t, locale } = useT();
  const stats = useNutritionStats(DAYS);
  const data = stats.data;
  if (!data) return null;

  const values = data.kcal.values;
  const loggedDays = data.kcal.logged.filter(Boolean).length;
  const weights = data.weight.values;
  if (loggedDays < 2 && weights.length < 2) return null;

  // The series ends today and has one value per day.
  const today = new Date();
  const bars: BarDatum[] = values.map((value, index) => {
    const date = addDays(today, index - (values.length - 1));
    const logged = data.kcal.logged[index] === true && value != null;
    return {
      key: isoDay(date),
      label: weekdayLetter(locale, date),
      value: logged ? value : null,
      title: `${longDay(locale, date)}: ${logged ? `${num(value, 0)} ${t("unit.kcal")}` : t("food.day.none")}`,
      current: index === values.length - 1,
    };
  });
  const trend = TREND[data.weight_trend];
  const change = data.weight_trend_detail?.change_kg;

  return (
    <Section title={t("food.week.title")} tone="nutrition">
      <div className="space-y-4 rounded-card bg-paper-2 p-4">
        {loggedDays >= 2 && (
          <div>
            <Bars data={bars} goal={data.goal_kcal} label={t("food.week.title")} tone="nutrition" onPick={onPick} />
            {data.avg_kcal != null && (
              <p className="mt-3 text-sm text-ink-2">
                {t("food.week.avg", { n: num(data.avg_kcal, 0) })}
                {data.goal_kcal ? `, ${t("food.week.goal", { n: num(data.goal_kcal, 0) })}` : ""}
              </p>
            )}
          </div>
        )}
        {weights.length >= 2 && (
          <div className="flex items-center justify-between gap-4 border-t border-rule pt-4 first:border-t-0 first:pt-0">
            <div className="min-w-0">
              <p className="font-medium">{t("weight.title")}</p>
              <p className="mt-0.5 text-sm text-muted">
                {trend ? t(trend) : t("weight.trend.wait")}
                {change ? `, ${change > 0 ? "+" : ""}${num(change)} ${t("unit.kg")}` : ""}
              </p>
            </div>
            <Sparkline values={weights} label={t("weight.chart")} tone="nutrition" />
          </div>
        )}
      </div>
    </Section>
  );
}
