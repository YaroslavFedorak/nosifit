import { Dumbbell, Play, Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { useTrainingRecommendations, useTrainingSession, useTrainingToday } from "../../api/queries";
import { useSaveSession } from "../../api/mutations";
import { entriesOf, totalVolume } from "../../api/session";
import type { LoggedExercise } from "../../api/types";
import { Button, ButtonLink } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState, ErrorState, Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { num } from "../../lib/format";
import { DESKTOP, useMediaQuery } from "../../lib/useMediaQuery";
import { ExerciseCard } from "./ExerciseCard";
import { ExerciseTip, GuidanceCard } from "./TipsTab";
import { ExerciseSheet } from "./ExerciseSheet";
import { SetSheet } from "./SetSheet";
import { WeeklySets } from "./WeeklySets";

/**
 * Desktop only: under the weekly sets, the one muscle to focus on and two
 * exercises for it, so the side column carries as much as the workout beside it.
 */
function FocusRail() {
  const { t } = useT();
  const desktop = useMediaQuery(DESKTOP);
  const recommendations = useTrainingRecommendations(desktop);
  const focus = recommendations.data?.guidance?.muscles?.[0];
  const exercises = recommendations.data?.recommended_exercises?.slice(0, 2) ?? [];
  if (!desktop || (!focus && exercises.length === 0)) return null;

  return (
    <Card accent="training" aria-labelledby="rail-focus">
      <h2 id="rail-focus" className="text-base font-semibold">
        {t("tr.tips.focus")}
      </h2>
      <ul className="mt-3 space-y-2.5">
        {focus && <GuidanceCard item={focus} tone="accent" />}
        {exercises.map((item) => (
          <ExerciseTip key={item.slug ?? item.exercise} item={item} />
        ))}
      </ul>
      <ButtonLink to="/training?tab=tips" variant="ghost" block className="mt-3">
        {t("tr.tips.all")}
      </ButtonLink>
    </Card>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-2xl font-semibold leading-none tracking-tight tabular-nums">{value}</div>
      <div className="mt-1.5 text-xs text-fg-muted">{label}</div>
    </div>
  );
}

/** Today's workout. Every change is saved on the spot; there is no separate "save" step. */
export function TodayTab() {
  const { t } = useT();
  const [params] = useSearchParams();
  const session = useTrainingSession();
  const plan = useTrainingToday();
  const save = useSaveSession();
  const [adding, setAdding] = useState(params.get("sheet") === "exercise");
  const [editing, setEditing] = useState<{ id: string; index: number | null } | null>(null);

  if (session.isError) return <ErrorState onRetry={() => void session.refetch()} />;
  if (session.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-40" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    );
  }

  const exercises = session.data?.exercises ?? [];
  const sessionId = session.data?.id ?? null;
  const busy = save.isPending;
  const persist = (next: LoggedExercise[]) => save.mutate({ sessionId, exercises: next });
  const replace = (updated: LoggedExercise) => persist(exercises.map((item) => (item.id === updated.id ? updated : item)));
  const editingExercise = editing ? exercises.find((item) => item.id === editing.id) : undefined;
  const sets = exercises.reduce((sum, item) => sum + entriesOf(item).length, 0);
  const planned = exercises.length === 0 && plan.data && plan.data.plan.length > 0 ? plan.data.exercises : [];

  const startPlanned = () =>
    persist(planned.map((item) => ({ ...item, id: String(item.id), slug: item.slug ?? null, measurement_type: item.measurement_type ?? "reps" })));

  const addButton = (
    <Button variant="primary" size="lg" block icon={<Plus size={20} aria-hidden="true" />} disabled={busy} onClick={() => setAdding(true)}>
      {t("tr.add")}
    </Button>
  );

  return (
    <div className="grid gap-4 desk:grid-cols-[minmax(0,1fr)_22rem] desk:items-start">
      <div className="space-y-4">
        {exercises.length === 0 ? (
          <Card tone="glass" accent="training">
            <EmptyState icon={<Dumbbell size={22} />} title={t("tr.empty.title")} text={t("tr.empty.text")} />
            <div className="space-y-2">
              {addButton}
              {planned.length > 0 && (
                <Button block icon={<Play size={18} aria-hidden="true" />} disabled={busy} onClick={startPlanned}>
                  {t("tr.plan.cta")}
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <>
            <Card tone="glass" accent="training" className="tab:flex tab:items-center tab:justify-between tab:gap-8">
              <div className="grid grid-cols-3 gap-3 tab:max-w-md tab:flex-1">
                <Stat value={String(exercises.length)} label={t("tr.sum.exercises")} />
                <Stat value={String(sets)} label={t("tr.sum.sets")} />
                <Stat value={num(totalVolume(exercises), 0)} label={t("tr.sum.volume")} />
              </div>
              <div className="mt-4 tab:mt-0 tab:w-64 tab:shrink-0">{addButton}</div>
            </Card>
            {/* Cards keep a readable width and the grid adds columns as space allows. */}
            <ul className="grid grid-cols-[repeat(auto-fill,minmax(17rem,1fr))] gap-3">
              {exercises.map((exercise) => (
                <ExerciseCard
                  key={exercise.id}
                  exercise={exercise}
                  disabled={busy}
                  onEditSet={(index) => setEditing({ id: exercise.id, index })}
                  onAddSet={() => setEditing({ id: exercise.id, index: null })}
                  onRemove={() => persist(exercises.filter((item) => item.id !== exercise.id))}
                />
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="space-y-4">
        <WeeklySets />
        <FocusRail />
      </div>

      <ExerciseSheet
        open={adding}
        onClose={() => setAdding(false)}
        taken={new Set(exercises.map((item) => item.id))}
        onPick={(exercise) => persist([...exercises, exercise])}
      />
      {editing && editingExercise && (
        <SetSheet
          key={`${editing.id}:${editing.index}`}
          exercise={editingExercise}
          index={editing.index}
          onClose={() => setEditing(null)}
          onSave={replace}
        />
      )}
    </div>
  );
}
