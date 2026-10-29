import { ChevronDown, Plus } from "lucide-react";
import { useState } from "react";
import { useDeleteEntry, useUpdateEntry } from "../../api/mutations";
import { MEAL_CATEGORIES, type Meal, type MealCategory, type MealItem, type NutritionDay } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Collapse } from "../../components/ui/Collapse";
import { Sheet } from "../../components/ui/Sheet";
import { parseDecimal, Stepper } from "../../components/ui/Stepper";
import { useT, type I18n } from "../../i18n";
import { cn } from "../../lib/cn";
import { clamp, num } from "../../lib/format";

export function unitLabel(unit: string, t: I18n["t"]): string {
  return unit === "g" ? t("unit.g") : unit === "ml" ? t("unit.ml") : unit;
}

function ItemSheet({ item, onClose }: { item: MealItem; onClose: () => void }) {
  const { t } = useT();
  const update = useUpdateEntry();
  const remove = useDeleteEntry();
  const [amount, setAmount] = useState(num(item.amount));
  const parsed = parseDecimal(amount);
  const busy = update.isPending || remove.isPending;

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("nu.item.title")}
      footer={
        <div className="flex gap-2">
          <Button variant="danger" disabled={busy} onClick={() => remove.mutate(item.id, { onSuccess: onClose })}>
            {t("common.remove")}
          </Button>
          <Button
            variant="primary"
            size="lg"
            className="flex-1"
            disabled={busy || parsed === null || parsed <= 0}
            onClick={() => parsed && update.mutate({ id: item.id, amount: clamp(parsed, 1, 5000), unit: item.unit }, { onSuccess: onClose })}
          >
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <p className="pb-4 pt-1 text-sm text-fg-muted">{item.name}</p>
      <Stepper label={`${t("nu.item.amount")}, ${unitLabel(item.unit, t)}`} value={amount} onChange={setAmount} step={10} min={1} max={5000} />
    </Sheet>
  );
}

function MealRow({ category, meal, onAdd, onEdit }: { category: MealCategory; meal: Meal | undefined; onAdd: () => void; onEdit: (item: MealItem) => void }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const name = t(`nu.meal.${category}` as "nu.meal.breakfast");
  const panel = `meal-${category}`;
  const items = meal?.items ?? [];

  return (
    <li className="border-t border-line first:border-t-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panel}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-tap-lg w-full items-center justify-between gap-3 py-2 text-left"
      >
        <span className="text-base font-semibold">{name}</span>
        <span className="flex items-center gap-2">
          <span className={cn("text-sm tabular-nums", items.length ? "text-fg-muted" : "text-fg-soft")}>
            {items.length ? `${num(meal?.total_calories, 0)} ${t("unit.kcal")}` : "–"}
          </span>
          <ChevronDown size={18} className={cn("text-fg-soft transition-transform", open && "rotate-180")} aria-hidden="true" />
        </span>
      </button>
      <Collapse open={open} id={panel}>
        <div className="space-y-1 pb-3">
          {items.length === 0 && <p className="py-1 text-sm text-fg-muted">{t("nu.meal.empty")}</p>}
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onEdit(item)}
              className="flex min-h-tap w-full items-center justify-between gap-3 rounded-xl px-2 py-1.5 text-left transition hover:bg-white/5"
            >
              <span className="min-w-0 text-sm font-medium leading-snug">{item.name}</span>
              <span className="shrink-0 text-right text-xs tabular-nums text-fg-muted">
                <span className="block">
                  {num(item.amount)} {unitLabel(item.unit, t)}
                </span>
                <span className="block">
                  {num(item.calories, 0)} {t("unit.kcal")}
                </span>
              </span>
            </button>
          ))}
          <Button variant="ghost" block icon={<Plus size={16} aria-hidden="true" />} onClick={onAdd}>
            {t("nu.addTo", { meal: name })}
          </Button>
        </div>
      </Collapse>
    </li>
  );
}

/** The four meals, collapsed until the user opens one. */
export function MealsCard({ day, onAdd }: { day: NutritionDay; onAdd: (category: MealCategory) => void }) {
  const { t } = useT();
  const [editing, setEditing] = useState<MealItem | null>(null);
  const byCategory = new Map(day.meals.map((meal) => [meal.category, meal]));

  return (
    <Card accent="nutrition" aria-labelledby="meals-title">
      <h2 id="meals-title" className="text-base font-semibold">
        {t("nu.meals")}
      </h2>
      <ul className="mt-1">
        {MEAL_CATEGORIES.map((category) => (
          <MealRow key={category} category={category} meal={byCategory.get(category)} onAdd={() => onAdd(category)} onEdit={setEditing} />
        ))}
      </ul>
      {editing && <ItemSheet key={editing.id} item={editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
