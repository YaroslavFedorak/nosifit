import { Dumbbell, ListChecks, Moon, Scale, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { useNavigate } from "react-router";
import { useHabits, useTrainingSession, useWeight } from "../../api/queries";
import type { Tone } from "../../design/tokens";
import { mealForNow } from "../../domain/nutrition";
import { useT } from "../../i18n";
import { num } from "../../lib/format";
import { Row } from "../../ui/Layout";
import { Sheet } from "../../ui/Sheet";
import { WaterQuick } from "../nutrition/WaterQuick";
import type { LogRequest } from "./LogProvider";

function Glyph({ icon: Icon, tone }: { icon: LucideIcon; tone: Tone }) {
  return (
    <span data-tone={tone} className="text-tone" aria-hidden="true">
      <Icon size={20} />
    </span>
  );
}

/**
 * Everything that can be recorded, one tap away from any screen. Water is
 * added right here; the rest opens its own short form.
 */
export function QuickLogSheet({ onClose, onPick }: { onClose: () => void; onPick: (request: LogRequest) => void }) {
  const { t, tn } = useT();
  const navigate = useNavigate();
  const session = useTrainingSession();
  const habits = useHabits();
  const weight = useWeight();
  const meal = mealForNow();
  const list = habits.data ?? [];
  const done = list.filter((habit) => habit.completed).length;

  const go = (to: string) => {
    onClose();
    navigate(to);
  };

  return (
    <Sheet open onClose={onClose} title={t("log.title")}>
      <div className="-mx-4 divide-y divide-rule border-y border-rule">
        <Row
          leading={<Glyph icon={UtensilsCrossed} tone="nutrition" />}
          title={t("log.food")}
          subtitle={t("log.foodTo", { meal: t(`meal.${meal}`) })}
          chevron
          onClick={() => onPick({ kind: "food", category: meal })}
        />
        <div className="px-4 py-3">
          <WaterQuick />
        </div>
        <Row
          leading={<Glyph icon={Dumbbell} tone="training" />}
          title={session.data ? t("log.workoutContinue") : t("log.workout")}
          subtitle={session.data ? tn("count.sets", session.data.totals.sets) : t("log.workoutHint")}
          chevron
          onClick={() => go(session.data ? "/training" : "/training?sheet=exercise")}
        />
        <Row leading={<Glyph icon={Moon} tone="recovery" />} title={t("log.sleep")} subtitle={t("log.sleepHint")} chevron onClick={() => onPick({ kind: "sleep" })} />
        {list.length > 0 && (
          <Row
            leading={<Glyph icon={ListChecks} tone="recovery" />}
            title={t("log.habits")}
            subtitle={t("habits.count", { done, total: list.length })}
            chevron
            onClick={() => go("/recovery")}
          />
        )}
        <Row
          leading={<Glyph icon={Scale} tone="nutrition" />}
          title={t("log.weight")}
          subtitle={weight.data?.weight ? `${num(weight.data.weight)} ${t("unit.kg")}` : t("log.weightHint")}
          chevron
          onClick={() => onPick({ kind: "weight" })}
        />
      </div>
    </Sheet>
  );
}
