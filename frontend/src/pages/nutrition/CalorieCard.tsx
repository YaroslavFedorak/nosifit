import { Plus } from "lucide-react";
import type { NutritionDay } from "../../api/types";
import { Bar } from "../../components/ui/Bar";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Ring } from "../../components/ui/Ring";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { num, ratio } from "../../lib/format";

function Macro({ label, value, goal }: { label: string; value: number; goal: number }) {
  const { t } = useT();
  const share = ratio(value, goal);
  return (
    <li className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className={cn("tabular-nums", share > 1.1 ? "text-warn" : "text-fg-muted")}>
          {num(value, 0)} / {goal > 0 ? num(goal, 0) : "–"} {t("unit.g")}
        </span>
      </div>
      <Bar value={share} tone={share > 1.1 ? "warn" : "accent"} label={label} />
    </li>
  );
}

/**
 * Remaining calories as a ring, protein / fat / carbs as bars. The page's one
 * status card. On a phone the parts stack; from the tablet breakpoint the ring
 * sits on the left and the bars fill the width beside it.
 */
export function CalorieCard({ day, onAdd }: { day: NutritionDay; onAdd: () => void }) {
  const { t } = useT();
  const hasGoal = day.goals_available && day.kcal_goal > 0;
  const over = hasGoal && day.kcal_remaining < 0;

  return (
    <Card
      tone="hero"
      accent="nutrition"
      strip
      aria-label={t("nu.title")}
      className="tab:grid tab:grid-cols-[auto_minmax(0,1fr)] tab:items-center tab:gap-x-10"
    >
      <div className="flex items-center gap-5 tab:flex-col tab:gap-3 tab:text-center">
        <Ring
          value={hasGoal ? ratio(day.kcal, day.kcal_goal) : 0}
          size={148}
          stroke={12}
          glow
          label={`${num(hasGoal ? Math.abs(day.kcal_remaining) : day.kcal, 0)} ${over ? t("nu.over") : t("nu.left")}`}
        >
          <div>
            <div className="text-3xl font-semibold leading-none tracking-tight tabular-nums">
              {num(hasGoal ? Math.abs(day.kcal_remaining) : day.kcal, 0)}
            </div>
            <div className="mt-1.5 text-xs font-medium text-fg-muted">
              {hasGoal ? (over ? t("nu.over") : t("nu.left")) : t("unit.kcal")}
            </div>
          </div>
        </Ring>
        <div className="min-w-0 space-y-1 text-sm">
          <p className="font-medium">{t("nu.eaten", { n: num(day.kcal, 0) })}</p>
          {hasGoal && <p className="text-fg-muted">{t("nu.goal", { n: num(day.kcal_goal, 0) })}</p>}
        </div>
      </div>

      <ul className="mt-6 space-y-3.5 tab:mt-0">
        <Macro label={t("nu.protein")} value={day.protein} goal={day.protein_goal} />
        <Macro label={t("nu.fat")} value={day.fat} goal={day.fat_goal} />
        <Macro label={t("nu.carbs")} value={day.carb} goal={day.carb_goal} />
      </ul>

      <Button variant="primary" size="lg" block className="mt-5 tab:col-span-2 tab:mt-6" icon={<Plus size={20} aria-hidden="true" />} onClick={onAdd}>
        {t("nu.addFood")}
      </Button>
    </Card>
  );
}
