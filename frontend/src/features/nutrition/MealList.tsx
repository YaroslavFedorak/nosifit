import { BookmarkPlus, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useCreateDish } from "../../api/mutations";
import { MEAL_CATEGORIES, type Meal, type MealCategory, type MealItem } from "../../api/types";
import type { DiaryDay } from "../../domain/nutrition";
import { useT } from "../../i18n";
import { errorCode } from "../../lib/api";
import { num } from "../../lib/format";
import { toast } from "../../lib/toast";
import { Button, IconButton } from "../../ui/Button";
import { TextField } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";
import { EntrySheet } from "./EntrySheet";
import { unitLabel } from "./FoodPicker";

/** Saves a meal's foods as a dish, to add them together next time. */
function SaveDishSheet({ meal, mealName, onClose }: { meal: Meal; mealName: string; onClose: () => void }) {
  const { t } = useT();
  const create = useCreateDish();
  const [name, setName] = useState("");
  const duplicate = errorCode(create.error) === "duplicate_dish";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), items: meal.items.map((item) => ({ productId: item.product_id, amount: item.amount, unit: item.unit })) },
      {
        onSuccess: () => {
          toast(t("dish.saved"));
          onClose();
        },
      },
    );
  };

  return (
    <Sheet open tone="nutrition" onClose={onClose} title={t("dish.save")}>
      <form onSubmit={submit} className="space-y-4">
        <TextField
          label={t("dish.name")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={mealName}
          autoFocus
          autoComplete="off"
          maxLength={120}
          hint={t("dish.hint", { n: meal.items.length })}
          error={duplicate ? t("dish.duplicate") : create.isError ? t("common.failed") : null}
        />
        <Button type="submit" variant="primary" size="lg" block disabled={!name.trim()} busy={create.isPending}>
          {t("common.save")}
        </Button>
      </form>
    </Sheet>
  );
}

function MealBlock({
  category,
  meal,
  onAdd,
  onEdit,
  onSave,
}: {
  category: MealCategory;
  meal: Meal | undefined;
  onAdd: () => void;
  onEdit: (item: MealItem) => void;
  onSave: (meal: Meal) => void;
}) {
  const { t } = useT();
  const name = t(`meal.${category}`);
  const items = meal?.items ?? [];

  return (
    <section aria-label={name}>
      <div className="flex min-h-[3.25rem] items-center gap-2 pl-4 pr-2">
        <h3 className="min-w-0 flex-1 truncate">{name}</h3>
        {items.length > 0 && (
          <span className="figure text-sm font-normal text-ink-2">
            {num(meal?.total_calories, 0)} {t("unit.kcal")}
          </span>
        )}
        {meal && items.length > 1 && (
          <IconButton label={t("dish.saveMeal", { meal: name })} onClick={() => onSave(meal)}>
            <BookmarkPlus size={18} />
          </IconButton>
        )}
        <IconButton tonal label={t("food.addTo", { meal: name })} onClick={onAdd}>
          <Plus size={18} />
        </IconButton>
      </div>
      {items.length > 0 && (
        <ul className="pb-1">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onEdit(item)}
                className="flex min-h-11 w-full items-baseline gap-3 px-4 py-2 text-left transition-colors duration-150 hover:bg-paper-3"
              >
                <span className="min-w-0 flex-1 truncate text-ink-2">{item.name}</span>
                <span className="figure shrink-0 text-sm font-normal text-muted">
                  {num(item.amount)} {unitLabel(item.unit, t)}
                </span>
                <span className="figure w-12 shrink-0 text-right text-sm font-normal text-ink-2">{num(item.calories, 0)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * The four meals of a day, always open. A meal with nothing in it is one
 * line with a plus; a logged food is a line that opens its amount.
 */
export function MealList({ day, onAdd }: { day: DiaryDay; onAdd: (category: MealCategory) => void }) {
  const { t } = useT();
  const [editing, setEditing] = useState<MealItem | null>(null);
  const [saving, setSaving] = useState<Meal | null>(null);
  const byCategory = new Map(day.meals.map((meal) => [meal.category, meal]));

  return (
    <>
      <div className="divide-y divide-rule overflow-hidden rounded-card bg-paper-2">
        {MEAL_CATEGORIES.map((category) => (
          <MealBlock key={category} category={category} meal={byCategory.get(category)} onAdd={() => onAdd(category)} onEdit={setEditing} onSave={setSaving} />
        ))}
      </div>
      {editing && <EntrySheet key={editing.id} item={editing} onClose={() => setEditing(null)} />}
      {saving && <SaveDishSheet meal={saving} mealName={t(`meal.${saving.category}`)} onClose={() => setSaving(null)} />}
    </>
  );
}
