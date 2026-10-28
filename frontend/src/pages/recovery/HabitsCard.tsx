import { Check, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useAddHabit, useRemoveHabit, useToggleHabit } from "../../api/mutations";
import { useHabitCatalog } from "../../api/queries";
import type { Habit, RecoverySnapshot } from "../../api/types";
import { Button, IconButton } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Chip";
import { Sheet } from "../../components/ui/Sheet";
import { EmptyState, Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";

const LIMIT = 6;

function CatalogSheet({ taken, onClose }: { taken: Set<number>; onClose: () => void }) {
  const { t } = useT();
  const catalog = useHabitCatalog(true);
  const add = useAddHabit();

  return (
    <Sheet open onClose={onClose} title={t("rc.habits.catalog")}>
      {catalog.isPending ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-16" />
          ))}
        </div>
      ) : (
        <ul className="space-y-1.5 pt-1">
          {(catalog.data ?? []).map((habit) => {
            const added = taken.has(habit.id);
            return (
              <li key={habit.id}>
                <button
                  type="button"
                  disabled={added || add.isPending}
                  onClick={() => add.mutate(habit.id)}
                  className={cn(
                    "flex min-h-14 w-full items-center justify-between gap-3 rounded-xl border border-line bg-surface-2/50 px-3.5 py-2.5 text-left transition hover:bg-surface-2 active:scale-[0.99]",
                    added && "opacity-60",
                  )}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold leading-snug">{habit.name}</span>
                    {habit.description && <span className="block text-xs text-fg-muted">{habit.description}</span>}
                  </span>
                  {added ? (
                    <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-ok">
                      <Check size={14} aria-hidden="true" />
                      {t("rc.habits.added")}
                    </span>
                  ) : (
                    <>
                      {habit.premium_only && <Badge tone="accent">Premium</Badge>}
                      <Plus size={18} className="shrink-0 text-fg-muted" aria-hidden="true" />
                    </>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Sheet>
  );
}

function HabitRow({ habit, editing }: { habit: Habit; editing: boolean }) {
  const { t } = useT();
  const text = useServerText();
  const toggle = useToggleHabit();
  const remove = useRemoveHabit();

  return (
    <li className="flex items-center gap-1 border-t border-line">
      <button
        type="button"
        role="checkbox"
        aria-checked={habit.completed}
        disabled={editing}
        onClick={() => toggle.mutate(habit)}
        className="flex min-h-14 flex-1 items-center gap-3 py-2 text-left disabled:opacity-70"
      >
        <span
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-lg border-2 transition",
            habit.completed ? "border-recovery bg-recovery text-canvas" : "border-line-strong text-transparent",
          )}
          aria-hidden="true"
        >
          <Check size={16} strokeWidth={3} />
        </span>
        <span className="min-w-0">
          <span className={cn("block text-sm font-medium leading-snug", habit.completed && "text-fg-muted")}>{habit.name}</span>
          <span className="block text-xs text-fg-soft">{text.text(`categories.${habit.category}`) ?? habit.category}</span>
        </span>
      </button>
      {editing && (
        <IconButton label={t("rc.habits.remove")} disabled={remove.isPending} onClick={() => remove.mutate(habit.user_habit_id)} className="text-danger">
          <Trash2 size={18} />
        </IconButton>
      )}
    </li>
  );
}

/** Habits as a plain checklist: full names, 56px rows, no inner scrolling. */
export function HabitsCard({ snapshot }: { snapshot: RecoverySnapshot }) {
  const { t } = useT();
  const [catalog, setCatalog] = useState(false);
  const [editing, setEditing] = useState(false);
  const [all, setAll] = useState(false);
  const habits = snapshot.habits;
  const done = habits.filter((habit) => habit.completed).length;
  const shown = all ? habits : habits.slice(0, LIMIT);

  return (
    <Card accent="recovery" aria-labelledby="habits-title">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="habits-title" className="text-base font-semibold">
            {t("rc.habits.title")}
          </h2>
          {habits.length > 0 && <p className="mt-0.5 text-sm text-fg-muted">{t("rc.habits.sum", { done, total: habits.length })}</p>}
        </div>
        <Button icon={<Plus size={16} aria-hidden="true" />} onClick={() => setCatalog(true)}>
          {t("common.add")}
        </Button>
      </div>

      {habits.length === 0 ? (
        <EmptyState icon={<Check size={22} />} title={t("rc.habits.none")} />
      ) : (
        <>
          <ul className="mt-2 grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-x-6">
            {shown.map((habit) => (
              <HabitRow key={habit.user_habit_id} habit={habit} editing={editing} />
            ))}
          </ul>
          <div className="mt-1 flex items-center justify-between gap-2">
            {habits.length > LIMIT ? (
              <Button variant="ghost" onClick={() => setAll((value) => !value)}>
                {all ? t("common.showLess") : t("common.all", { n: habits.length })}
              </Button>
            ) : (
              <span />
            )}
            <Button variant="ghost" aria-pressed={editing} onClick={() => setEditing((value) => !value)}>
              {editing ? t("common.done") : t("common.edit")}
            </Button>
          </div>
        </>
      )}

      {catalog && <CatalogSheet taken={new Set(habits.map((habit) => habit.id))} onClose={() => setCatalog(false)} />}
    </Card>
  );
}
