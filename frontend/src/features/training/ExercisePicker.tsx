import { useQuery } from "@tanstack/react-query";
import { Check, Plus, Search, X } from "lucide-react";
import { useRef, useState } from "react";
import { useExerciseOptions } from "../../api/queries";
import type { ExerciseOption, Measurement } from "../../api/types";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { api } from "../../lib/api";
import { cn } from "../../lib/cn";
import { num } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { Button, IconButton } from "../../ui/Button";
import { Chips, type Option } from "../../ui/Choice";
import { Empty, SkeletonRows } from "../../ui/Feedback";
import { controlClass } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

/** The groups people look for exercises by; the catalog knows more muscles than a filter needs. */
const GROUPS = ["chest", "lats", "upper-back", "shoulders", "biceps", "triceps", "abs", "glutes", "quads", "hamstrings", "calves"] as const;
type Group = (typeof GROUPS)[number];
type Filter = "recent" | Group;

interface CatalogExercise {
  id: string;
  slug: string | null;
  name: string;
  measurement_type: Measurement;
  load_type?: string | null;
}

const useGroupExercises = (group: Group | null) =>
  useQuery({
    queryKey: ["training", "catalog", group],
    queryFn: async () =>
      (await api.get<{ items: CatalogExercise[] }>(`/api/training/exercises?muscle=${group}&per_page=60`)).items.map<ExerciseOption>((item) => ({
        id: item.id,
        slug: item.slug,
        name: item.name,
        measurement_type: item.measurement_type,
      })),
    enabled: group !== null,
    staleTime: 10 * 60_000,
  });

/**
 * Finds an exercise: by name, among the ones done recently, or by muscle
 * group. The sheet stays open while several are picked.
 */
export function ExercisePicker({
  title,
  taken,
  busy = false,
  onPick,
  onClose,
}: {
  title: string;
  /** Ids already in the list being built. */
  taken: Set<string>;
  busy?: boolean;
  onPick: (option: ExerciseOption) => void;
  onClose: () => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("recent");
  const input = useRef<HTMLInputElement>(null);
  const search = useDebounced(query.trim());
  const searching = search.length > 0;
  const group = !searching && filter !== "recent" ? filter : null;

  const found = useExerciseOptions(search, searching || filter === "recent");
  const grouped = useGroupExercises(group);
  const source = group ? grouped : found;
  const options = source.data ?? [];

  const filters: Option<Filter>[] = [{ id: "recent", label: t("exercise.recent") }, ...GROUPS.map((id) => ({ id, label: text.muscle(id) }))];

  const lastTime = (option: ExerciseOption): string | null => {
    const last = option.last;
    if (!last) return null;
    const first = last.set_entries?.[0];
    const value = first?.reps ?? last.reps ?? (last.duration_sec ? `${last.duration_sec} ${t("unit.s")}` : "");
    const load = first?.load ?? last.load;
    return t("exercise.last", { sets: `${last.sets} × ${value}${load ? ` × ${num(load)} ${t("unit.kg")}` : ""}` });
  };

  return (
    <Sheet
      open
      size="tall"
      onClose={onClose}
      title={title}
      footer={
        taken.size > 0 ? (
          <Button variant="primary" size="lg" block onClick={onClose}>
            {t("common.done")}
          </Button>
        ) : undefined
      }
    >
      <div data-tone="training" className="space-y-3">
        <div className="relative">
          <Search size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            ref={input}
            type="search"
            inputMode="search"
            enterKeyHint="search"
            autoFocus
            autoComplete="off"
            aria-label={t("exercise.search")}
            placeholder={t("exercise.search")}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={cn(controlClass, "px-10")}
          />
          {query && (
            <IconButton
              label={t("food.clear")}
              className="absolute right-1 top-1/2 -translate-y-1/2"
              onClick={() => {
                setQuery("");
                input.current?.focus();
              }}
            >
              <X size={18} />
            </IconButton>
          )}
        </div>

        {!searching && <Chips label={t("exercise.groups")} options={filters} value={filter} onChange={setFilter} />}

        {source.isPending ? (
          <SkeletonRows rows={6} />
        ) : options.length === 0 ? (
          <Empty
            title={searching ? t("exercise.none", { query: search }) : t("exercise.recentEmpty")}
            text={searching ? t("exercise.noneText") : t("exercise.recentEmptyText")}
          />
        ) : (
          <ul className="-mx-4 divide-y divide-rule border-y border-rule">
            {options.map((option) => {
              const added = taken.has(String(option.id));
              const last = lastTime(option);
              return (
                <li key={option.id}>
                  <button
                    type="button"
                    disabled={added || busy}
                    onClick={() => onPick({ ...option, id: String(option.id) })}
                    className="flex min-h-[3.25rem] w-full items-center gap-3 px-4 py-2 text-left transition-colors duration-150 hover:bg-paper-3 disabled:cursor-not-allowed"
                  >
                    <span className="min-w-0 flex-1">
                      <span className={cn("block truncate font-medium", added && "text-muted")}>{text.exercise(option.slug, option.name)}</span>
                      {last && <span className="block truncate text-sm text-muted">{last}</span>}
                    </span>
                    {added ? <Check size={18} className="anim-tick text-tone" aria-label={t("exercise.added")} /> : <Plus size={18} className="text-muted" aria-hidden="true" />}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Sheet>
  );
}
