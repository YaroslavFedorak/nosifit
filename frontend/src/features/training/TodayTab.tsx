import { Check, Play, Plus } from "lucide-react";
import { useState } from "react";
import { useCompletePlanDay } from "../../api/mutations";
import { usePlanWeek, usePlans, useTrainingRecommendations } from "../../api/queries";
import type { ExerciseOption, LoggedExercise, PlanEntry, RecommendedExercise } from "../../api/types";
import { entriesOf, exerciseFromOption, exerciseFromPlan, planDayEntries, totalSets, totalVolume, withEntries } from "../../domain/training";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { api } from "../../lib/api";
import { bootstrap } from "../../lib/bootstrap";
import { num } from "../../lib/format";
import { toast } from "../../lib/toast";
import { Button, IconButton } from "../../ui/Button";
import { ErrorNote, Skeleton } from "../../ui/Feedback";
import { Group, Row, Section, Stat } from "../../ui/Layout";
import { ExercisePicker } from "./ExercisePicker";
import { ExerciseSheet } from "./ExerciseSheet";
import { WorkoutPlayer, type PlayerItem } from "./WorkoutPlayer";
import { planLabel, setsLabel, useWorkout } from "./useWorkout";

/** The plan's exercises with what is already logged today folded in, so a workout can be resumed. */
function resume(planned: PlanEntry[], logged: LoggedExercise[]): PlayerItem[] {
  const byId = new Map(logged.map((exercise) => [exercise.id, exercise]));
  const items: PlayerItem[] = planned.map((entry) => {
    const target = exerciseFromPlan(entry);
    const done = byId.get(target.id);
    if (!done) return { exercise: target, done: 0 };
    byId.delete(target.id);
    const doneSets = entriesOf(done);
    const rest = entriesOf(target).slice(doneSets.length);
    return { exercise: withEntries({ ...target, ...done }, [...doneSets, ...rest]), done: doneSets.length };
  });
  for (const extra of byId.values()) items.push({ exercise: extra, done: entriesOf(extra).length });
  return items;
}

/** A recommended exercise carries a slug, not an id: the search finds the catalog entry. */
async function findBySlug(slug: string): Promise<ExerciseOption | null> {
  const { items } = await api.get<{ items: ExerciseOption[] }>(`/api/training/exercises/search?q=${encodeURIComponent(slug)}&limit=5&locale=${bootstrap.locale}`);
  return items.find((item) => item.slug === slug) ?? null;
}

/** What to train next, in the model's own words, with a way to add each exercise. */
function Suggestions({ taken, busy, onAdd }: { taken: Set<string>; busy: boolean; onAdd: (option: ExerciseOption) => void }) {
  const { t } = useT();
  const text = useServerText();
  const recommendations = useTrainingRecommendations();
  const [resolving, setResolving] = useState<string | null>(null);
  const focus = recommendations.data?.guidance?.muscles?.[0];
  const exercises = (recommendations.data?.recommended_exercises ?? []).filter((item) => item.slug).slice(0, 3);
  if (!text.ready || (!focus && exercises.length === 0)) return null;

  const reason = focus ? text.text(focus.reasons[0], focus.params) : null;
  const add = async (item: RecommendedExercise) => {
    if (!item.slug) return;
    setResolving(item.slug);
    try {
      const option = await findBySlug(item.slug);
      if (option && !taken.has(String(option.id))) onAdd(option);
      else if (!option) toast(t("common.failed"), "error");
    } catch {
      toast(t("common.failed"), "error");
    } finally {
      setResolving(null);
    }
  };

  return (
    <Section title={t("workout.next")}>
      {focus && (
        <div className="mb-3">
          <p className="font-medium">{text.muscle(focus.muscle)}</p>
          {reason && <p className="mt-0.5 max-w-[52ch] text-sm text-ink-2">{reason}</p>}
        </div>
      )}
      {exercises.length > 0 && (
        <Group>
          {exercises.map((item) => (
            <div key={item.slug} className="flex items-center">
              <div className="min-w-0 flex-1 px-4 py-2.5">
                <p className="truncate font-medium">{text.exercise(item.slug, item.exercise)}</p>
                <p className="truncate text-sm text-muted">
                  {planLabel(item, t)}, {item.target_muscles.slice(0, 2).map((muscle) => text.muscle(muscle).toLocaleLowerCase()).join(", ")}
                </p>
              </div>
              <IconButton tonal label={t("workout.addNamed", { name: text.exercise(item.slug, item.exercise) })} className="mr-2" disabled={busy || resolving !== null} onClick={() => void add(item)}>
                <Plus size={18} />
              </IconButton>
            </div>
          ))}
        </Group>
      )}
    </Section>
  );
}

/**
 * Today's workout. Three situations, one screen: a workout already being
 * logged, a planned one waiting to start, or a clean day with one button.
 */
export function TodayTab({ openPicker }: { openPicker: boolean }) {
  const { t, tn } = useT();
  const text = useServerText();
  const workout = useWorkout();
  const plans = usePlans();
  const active = (plans.data ?? []).find((plan) => plan.is_active) ?? null;
  const week = usePlanWeek(active?.id);
  const complete = useCompletePlanDay();
  const [picking, setPicking] = useState(openPicker);
  const [editing, setEditing] = useState<string | null>(null);
  const [player, setPlayer] = useState<PlayerItem[] | null>(null);

  if (workout.failed) return <ErrorNote onRetry={workout.retry} />;
  if (workout.loading || plans.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-24" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  const exercises = workout.exercises;
  const today = week.data?.days.find((day) => day.is_today);
  const planned = active && today && !today.rest ? planDayEntries(active, today.key) : [];
  const taken = new Set(exercises.map((exercise) => exercise.id));
  const editingExercise = editing ? exercises.find((exercise) => exercise.id === editing) : undefined;
  const add = (option: ExerciseOption) => void workout.persist([...exercises, exerciseFromOption(option)]).catch(() => undefined);
  const unfinishedPlan = planned.length > 0 && planned.some((entry) => !taken.has(String(entry.exercise.id)));

  return (
    <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start" data-tone="training">
      <div className="space-y-6 desk:col-span-7">
        {exercises.length > 0 ? (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Stat value={exercises.length} label={t("workout.exercises")} />
              <Stat value={totalSets(exercises)} label={t("workout.sets")} />
              <Stat value={num(totalVolume(exercises), 0)} unit={t("unit.kg")} label={t("workout.volume")} />
            </div>
            <div className="flex flex-wrap gap-2">
              {unfinishedPlan && (
                <Button variant="primary" size="lg" icon={<Play size={18} aria-hidden="true" />} onClick={() => setPlayer(resume(planned, exercises))}>
                  {t("workout.resume")}
                </Button>
              )}
              <Button variant={unfinishedPlan ? "secondary" : "primary"} size="lg" icon={<Plus size={18} aria-hidden="true" />} onClick={() => setPicking(true)}>
                {t("exercise.add")}
              </Button>
            </div>
            <Group>
              {exercises.map((exercise) => (
                <Row
                  key={exercise.id}
                  title={text.exercise(exercise.slug, exercise.name)}
                  subtitle={setsLabel(exercise, t)}
                  chevron
                  onClick={() => setEditing(exercise.id)}
                />
              ))}
            </Group>
          </>
        ) : planned.length > 0 ? (
          <section aria-labelledby="plan-today">
            <h2 id="plan-today" className="text-xl">
              {t("workout.planned.title")}
            </h2>
            <p className="mt-1.5 text-ink-2">
              {active?.name}, {tn("count.exercises", planned.length)}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" size="lg" icon={<Play size={18} aria-hidden="true" />} onClick={() => setPlayer(resume(planned, []))}>
                {t("workout.start")}
              </Button>
              {active && today && (
                <Button size="lg" icon={<Check size={18} aria-hidden="true" />} busy={complete.isPending} onClick={() => complete.mutate({ planId: active.id, day: today.key })}>
                  {t("workout.markDone")}
                </Button>
              )}
            </div>
            <Group className="mt-6">
              {planned.map((entry) => (
                <Row key={String(entry.exercise.id)} title={text.exercise(entry.exercise.slug, entry.exercise.name)} trailing={<span className="figure font-normal">{planLabel(entry, t)}</span>} />
              ))}
            </Group>
          </section>
        ) : (
          <section aria-labelledby="start-title">
            <h2 id="start-title" className="text-xl">
              {t("workout.empty.title")}
            </h2>
            <p className="mt-1.5 max-w-[46ch] text-ink-2">{today?.rest && active ? t("workout.empty.rest") : t("workout.empty.text")}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" size="lg" icon={<Play size={18} aria-hidden="true" />} onClick={() => setPlayer([])}>
                {t("workout.start")}
              </Button>
              <Button size="lg" icon={<Plus size={18} aria-hidden="true" />} onClick={() => setPicking(true)}>
                {t("workout.logDone")}
              </Button>
            </div>
          </section>
        )}
      </div>

      <div className="desk:col-span-5">
        <Suggestions taken={taken} busy={workout.busy} onAdd={add} />
      </div>

      {picking && <ExercisePicker title={t("exercise.add")} taken={taken} busy={workout.busy} onPick={add} onClose={() => setPicking(false)} />}
      {editingExercise && (
        <ExerciseSheet
          key={editingExercise.id}
          exercise={editingExercise}
          busy={workout.busy}
          onClose={() => setEditing(null)}
          onSave={(next) =>
            void workout
              .persist(exercises.map((exercise) => (exercise.id === next.id ? next : exercise)))
              .then(() => setEditing(null))
              .catch(() => undefined)
          }
          onRemove={() =>
            void workout
              .persist(exercises.filter((exercise) => exercise.id !== editingExercise.id))
              .then(() => setEditing(null))
              .catch(() => undefined)
          }
        />
      )}
      {player && <WorkoutPlayer initial={player} persist={workout.persist} busy={workout.busy} onClose={() => setPlayer(null)} />}
    </div>
  );
}
