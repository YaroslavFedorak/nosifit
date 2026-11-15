import { Check, Plus } from "lucide-react";
import { useAddHabit, useRemoveHabit } from "../../api/mutations";
import { useHabitCatalog } from "../../api/queries";
import type { Habit, HabitCatalogItem } from "../../api/types";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { SkeletonRows } from "../../ui/Feedback";
import { Sheet } from "../../ui/Sheet";

/** Categories in the order a day goes: sleep first, then what is eaten and drunk, then movement and rest. */
export const CATEGORY_ORDER = ["sleep", "hydration", "nutrition", "activity", "recovery", "stress", "massage"];

export function byCategory<T extends { category: string }>(items: T[]): Array<[string, T[]]> {
  const groups = new Map<string, T[]>();
  for (const item of items) groups.set(item.category, [...(groups.get(item.category) ?? []), item]);
  return [...groups.entries()].sort(([a], [b]) => {
    const left = CATEGORY_ORDER.indexOf(a);
    const right = CATEGORY_ORDER.indexOf(b);
    return (left < 0 ? CATEGORY_ORDER.length : left) - (right < 0 ? CATEGORY_ORDER.length : right);
  });
}

/**
 * Every habit the app knows, by category. A tap adds a habit to the user's
 * list or takes it off; the list on the page behind follows at once.
 */
export function HabitCatalogSheet({ mine, onClose }: { mine: Habit[]; onClose: () => void }) {
  const { t } = useT();
  const text = useServerText();
  const catalog = useHabitCatalog(true);
  const add = useAddHabit();
  const remove = useRemoveHabit();
  const owned = new Map(mine.map((habit) => [habit.id, habit.user_habit_id]));
  const busy = add.isPending || remove.isPending;
  // Habits the account cannot add are left out rather than shown locked.
  const available = (catalog.data ?? []).filter((habit) => !habit.premium_only || owned.has(habit.id));

  const toggle = (habit: HabitCatalogItem) => {
    const userHabitId = owned.get(habit.id);
    if (userHabitId != null) remove.mutate(userHabitId);
    else add.mutate(habit.id);
  };

  return (
    <Sheet open size="tall" onClose={onClose} title={t("habits.catalog")}>
      {catalog.isPending ? (
        <SkeletonRows rows={6} />
      ) : (
        <div data-tone="recovery" className="space-y-5">
          <p className="text-sm text-muted">{t("habits.catalogHint")}</p>
          {byCategory(available).map(([category, habits]) => (
            <section key={category} aria-label={text.habitCategory(category)}>
              <h3 className="mb-1 text-sm text-muted">{text.habitCategory(category)}</h3>
              <ul className="-mx-4 divide-y divide-rule border-y border-rule">
                {habits.map((habit) => {
                  const added = owned.has(habit.id);
                  return (
                    <li key={habit.id}>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={added}
                        disabled={busy}
                        onClick={() => toggle(habit)}
                        className="flex min-h-[3.25rem] w-full items-center gap-3 px-4 py-2 text-left transition-colors duration-150 hover:bg-paper-3 disabled:cursor-progress"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block font-medium">{text.habit(habit.slug, habit.name)}</span>
                          <span className="block text-sm text-muted">{text.habitHint(habit.slug, habit.description)}</span>
                        </span>
                        <span
                          aria-hidden="true"
                          className={cn("grid size-8 shrink-0 place-items-center rounded-pill", added ? "bg-tone text-paper" : "bg-paper-3 text-ink-2")}
                        >
                          {added ? <Check size={16} strokeWidth={3} className="anim-tick" /> : <Plus size={16} />}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </Sheet>
  );
}
