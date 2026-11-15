import { Minus, Plus } from "lucide-react";
import { useAddWater } from "../../api/mutations";
import { useWater } from "../../api/queries";
import { useT } from "../../i18n";
import { isoDay, num, ratio } from "../../lib/format";
import { Progress } from "../../ui/Chart";
import { cn } from "../../lib/cn";

const GLASS_L = 0.25;
const BOTTLE_L = 0.5;

/**
 * Water for a day: the amount against the estimate, and one-tap amounts.
 * The minus takes a glass back when a tap was a mistake.
 */
export function WaterQuick({ date = isoDay(), compact = false, className }: { date?: string; compact?: boolean; className?: string }) {
  const { t } = useT();
  const water = useWater(date);
  const add = useAddWater();
  const liters = water.data?.amount ?? 0;
  const goal = water.data?.recommended ?? null;
  const change = (amount: number) => add.mutate({ liters: amount, date: date === isoDay() ? undefined : date });

  const amountButton = (amount: number) => (
    <button
      key={amount}
      type="button"
      disabled={add.isPending}
      onClick={() => change(amount)}
      className="press inline-flex min-h-control flex-1 items-center justify-center gap-1 whitespace-nowrap rounded-control bg-paper-3 px-3 text-sm font-medium hover:bg-paper-4 disabled:cursor-not-allowed disabled:opacity-55"
    >
      <Plus size={16} aria-hidden="true" />
      {num(amount * 1000, 0)} {t("unit.ml")}
    </button>
  );

  return (
    <div data-tone="water" className={cn("min-w-0", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <p className={cn("font-medium", compact && "text-sm")}>{t("water.title")}</p>
        {/* Before the first glass there is no amount to show, only what to aim for. */}
        <p className="figure text-sm font-normal text-ink-2" aria-live="polite">
          {liters > 0
            ? goal
              ? t("water.of", { n: num(liters, 2), goal: num(goal) })
              : t("water.amount", { n: num(liters, 2) })
            : goal
              ? t("water.goal", { goal: num(goal) })
              : null}
        </p>
      </div>
      {goal && liters > 0 ? <Progress value={ratio(liters, goal)} label={t("water.title")} className="mt-2" /> : null}
      <div className="mt-3 flex gap-2">
        {amountButton(GLASS_L)}
        {amountButton(BOTTLE_L)}
        <button
          type="button"
          aria-label={t("water.undo")}
          title={t("water.undo")}
          disabled={add.isPending || liters <= 0}
          onClick={() => change(-Math.min(GLASS_L, liters))}
          className="press inline-grid size-control shrink-0 place-items-center rounded-control text-ink-2 hover:bg-paper-3 hover:text-ink disabled:cursor-not-allowed disabled:opacity-55"
        >
          <Minus size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
