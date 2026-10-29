import { ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";
import { useWeeklySets } from "../../api/queries";
import type { WeeklyMuscle } from "../../api/types";
import { Bar } from "../../components/ui/Bar";
import { Card } from "../../components/ui/Card";
import { Collapse } from "../../components/ui/Collapse";
import { Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { ratio } from "../../lib/format";

const SHOWN = 3;
const gap = (muscle: WeeklyMuscle): number => (muscle.target_sets - muscle.sets) / (muscle.target_sets || 1);

function Row({ muscle }: { muscle: WeeklyMuscle }) {
  const { t } = useT();
  const text = useServerText();
  const name = text.muscle(muscle.muscle);
  // Whole sets on screen; "done" follows the same numbers, so the colour never disagrees with the text.
  const sets = Math.round(muscle.sets);
  const target = Math.max(1, Math.round(muscle.target_sets));
  const done = sets >= target;
  return (
    <li className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">{name}</span>
        <span className={cn("tabular-nums", done ? "text-ok" : "text-fg-muted")}>
          {t("tr.weekly.of", { sets, target })}
        </span>
      </div>
      <Bar value={ratio(muscle.sets, muscle.target_sets)} tone={done ? "ok" : "accent"} label={name} />
    </li>
  );
}

/** The three groups furthest from their weekly target; the rest sit behind "All N". */
export function WeeklySets() {
  const { t } = useT();
  const weekly = useWeeklySets();
  const [all, setAll] = useState(false);
  const sorted = useMemo(() => [...(weekly.data ?? [])].sort((a, b) => gap(b) - gap(a)), [weekly.data]);
  const lagging = sorted.slice(0, SHOWN);
  const rest = sorted.slice(SHOWN);

  return (
    <Card accent="training" aria-labelledby="weekly-title">
      <h2 id="weekly-title" className="text-base font-semibold">
        {t("tr.weekly.title")}
      </h2>
      <p className="mt-0.5 text-sm text-fg-muted">{t("tr.weekly.sub")}</p>

      {weekly.isPending ? (
        <div className="mt-4 space-y-4">
          <Skeleton className="h-9" />
          <Skeleton className="h-9" />
          <Skeleton className="h-9" />
        </div>
      ) : (
        <>
          <ul className="mt-4 grid gap-4 tab:grid-cols-2 tab:gap-x-8 desk:grid-cols-1">
            {lagging.map((muscle) => (
              <Row key={muscle.muscle} muscle={muscle} />
            ))}
          </ul>
          {rest.length > 0 && (
            <>
              <Collapse open={all} id="weekly-rest">
                <ul className="grid gap-4 pt-4 tab:grid-cols-2 tab:gap-x-8 desk:grid-cols-1">
                  {rest.map((muscle) => (
                    <Row key={muscle.muscle} muscle={muscle} />
                  ))}
                </ul>
              </Collapse>
              <button
                type="button"
                aria-expanded={all}
                aria-controls="weekly-rest"
                onClick={() => setAll((open) => !open)}
                className="mt-3 flex min-h-tap w-full items-center justify-center gap-1.5 rounded-xl text-sm font-semibold text-fg-muted transition hover:bg-white/5 hover:text-fg"
              >
                {all ? t("common.showLess") : t("common.all", { n: sorted.length })}
                <ChevronDown size={16} className={cn("transition-transform", all && "rotate-180")} aria-hidden="true" />
              </button>
            </>
          )}
        </>
      )}
    </Card>
  );
}
