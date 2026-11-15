import { useToggleHabit } from "../../api/mutations";
import type { Habit } from "../../api/types";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { Tick } from "../../ui/Choice";

/**
 * Habits as a checklist. A tap ticks a habit at once; the server is told
 * behind it and the tick rolls back if it refuses.
 */
export function HabitList({ habits, showCategory = false, className }: { habits: Habit[]; showCategory?: boolean; className?: string }) {
  const text = useServerText();
  const toggle = useToggleHabit();
  return (
    <ul data-tone="recovery" className={cn("divide-y divide-rule", className)}>
      {habits.map((habit) => (
        <li key={habit.user_habit_id}>
          <button
            type="button"
            role="checkbox"
            aria-checked={habit.completed}
            onClick={() => toggle.mutate(habit)}
            className="flex min-h-[3.25rem] w-full items-center gap-3 px-4 py-2 text-left transition-colors duration-150 hover:bg-paper-3"
          >
            <Tick checked={habit.completed} />
            <span className="min-w-0 flex-1">
              <span className={cn("block font-medium transition-colors duration-150", habit.completed && "text-muted")}>{text.habit(habit.slug, habit.name)}</span>
              {showCategory && <span className="block text-sm text-muted">{text.habitCategory(habit.category)}</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
