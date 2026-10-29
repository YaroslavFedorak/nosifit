import { Check, Search } from "lucide-react";
import { useState } from "react";
import { useExerciseOptions } from "../../api/queries";
import { exerciseFromOption } from "../../api/session";
import type { ExerciseOption, LoggedExercise } from "../../api/types";
import { Sheet } from "../../components/ui/Sheet";
import { EmptyState, Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { num } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";

/** Searchable list of exercises; with an empty query it shows the recent ones. */
export function ExerciseSheet({
  open,
  onClose,
  taken,
  onPick,
}: {
  open: boolean;
  onClose: () => void;
  taken: Set<string>;
  onPick: (exercise: LoggedExercise) => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const options = useExerciseOptions(search, open);

  const lastTime = (option: ExerciseOption): string | null => {
    const last = option.last;
    if (!last) return null;
    const entries = last.set_entries ?? [];
    const first = entries[0];
    const sets = `${last.sets} × ${first?.reps ?? last.reps ?? last.duration_sec ?? ""}${first?.load ? ` × ${num(first.load)} ${t("unit.kg")}` : ""}`;
    return t("tr.last", { sets });
  };

  return (
    <Sheet open={open} onClose={onClose} title={t("tr.add")}>
      <div className="sticky top-0 z-10 -mx-1 bg-surface px-1 pb-3">
        <label className="relative block">
          <span className="sr-only">{t("tr.search")}</span>
          <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-soft" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("tr.search")}
            autoComplete="off"
            className="min-h-tap-lg w-full rounded-xl border border-line-strong bg-surface-2 pl-10 pr-3 text-base outline-none placeholder:text-fg-soft focus:border-fg/40"
          />
        </label>
        <p className="mt-3 text-xs font-medium text-fg-muted">{search ? t("tr.results") : t("tr.recent")}</p>
      </div>

      {options.isPending ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-14" />
          ))}
        </div>
      ) : options.data && options.data.length > 0 ? (
        <ul className="space-y-1.5">
          {options.data.map((option) => {
            const added = taken.has(option.id);
            const last = lastTime(option);
            return (
              <li key={option.id}>
                <button
                  type="button"
                  disabled={added}
                  onClick={() => {
                    onPick(exerciseFromOption(option));
                    onClose();
                  }}
                  className={cn(
                    "flex min-h-14 w-full items-center justify-between gap-3 rounded-xl border border-line bg-surface-2/50 px-3.5 py-2 text-left transition hover:bg-surface-2 active:scale-[0.99]",
                    added && "opacity-50",
                  )}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold leading-snug">{text.exercise(option.slug, option.name)}</span>
                    {last && <span className="block text-xs text-fg-muted">{last}</span>}
                  </span>
                  {added && <Check size={18} className="shrink-0 text-ok" aria-hidden="true" />}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <EmptyState icon={<Search size={22} />} title={t("tr.none")} />
      )}
    </Sheet>
  );
}
