import { Link } from "react-router";
import type { DiaryDay } from "../../domain/nutrition";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { num, ratio } from "../../lib/format";
import { Progress } from "../../ui/Chart";

function Macro({ label, value, goal }: { label: string; value: number; goal: number }) {
  const { t } = useT();
  const share = ratio(value, goal);
  return (
    <div className="min-w-0">
      <dt className="truncate text-sm text-muted">{label}</dt>
      <dd className="mt-0.5">
        <span className="figure text-md">{num(value, 0)}</span>
        {goal > 0 && (
          <span className="text-sm text-muted">
            {" "}
            / {num(goal, 0)} {t("unit.g")}
          </span>
        )}
        {goal > 0 && <Progress value={share} label={label} tone={share > 1.1 ? "warn" : "nutrition"} className="mt-1.5" />}
      </dd>
    </div>
  );
}

/**
 * The day in one glance: energy against the target, then the three macros.
 * Before anything is logged it shows the target to aim for, never a row of zeros.
 */
export function DaySummary({ day, className }: { day: DiaryDay; className?: string }) {
  const { t } = useT();
  const logged = day.meals.some((meal) => meal.items.length > 0);
  const left = day.kcalGoal - day.kcal;

  if (!logged) {
    return (
      <div className={className}>
        <p className="font-medium">{day.isToday ? t("food.day.emptyToday") : t("food.day.emptyPast")}</p>
        <p className="mt-1 text-sm text-muted">
          {day.hasGoals ? (
            t("food.day.goal", { kcal: num(day.kcalGoal, 0), p: num(day.proteinGoal, 0), f: num(day.fatGoal, 0), c: num(day.carbsGoal, 0) })
          ) : (
            <NoGoals />
          )}
        </p>
      </div>
    );
  }

  return (
    <div data-tone="nutrition" className={className}>
      <div className="flex items-end justify-between gap-4">
        <p>
          <span className="figure text-figure text-ink">{num(day.kcal, 0)}</span>
          <span className="ml-1.5 text-sm text-muted">{day.hasGoals ? t("food.kcalOfGoal", { goal: num(day.kcalGoal, 0) }) : t("unit.kcal")}</span>
        </p>
        {day.hasGoals && (
          <p className={cn("pb-1 text-right text-sm", left < 0 ? "text-warn" : "text-ink-2")}>
            {left >= 0 ? t("food.left", { n: num(left, 0) }) : t("food.over", { n: num(-left, 0) })}
          </p>
        )}
      </div>
      {day.hasGoals ? (
        <Progress value={ratio(day.kcal, day.kcalGoal)} label={t("food.energy")} tone={left < -day.kcalGoal * 0.1 ? "warn" : "nutrition"} className="mt-3 h-2" />
      ) : (
        <p className="mt-2 text-sm text-muted">
          <NoGoals />
        </p>
      )}
      <dl className="mt-4 grid grid-cols-3 gap-4">
        <Macro label={t("food.protein")} value={day.protein} goal={day.hasGoals ? day.proteinGoal : 0} />
        <Macro label={t("food.fat")} value={day.fat} goal={day.hasGoals ? day.fatGoal : 0} />
        <Macro label={t("food.carbs")} value={day.carbs} goal={day.hasGoals ? day.carbsGoal : 0} />
      </dl>
    </div>
  );
}

/** Targets come from the profile; without age, height and weight there are none. */
function NoGoals() {
  const { t } = useT();
  return (
    <>
      {t("food.noGoals")}{" "}
      <Link to="/profile" className="font-medium text-ink underline underline-offset-4 hover:text-accent">
        {t("food.noGoalsLink")}
      </Link>
    </>
  );
}
