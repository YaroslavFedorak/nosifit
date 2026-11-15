import { Check, Plus, Settings2, Trash2, Wand2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useCompletePlanDay, useDeletePlan, useGeneratePlan, useSavePlan } from "../../api/mutations";
import { usePlanWeek, usePlans } from "../../api/queries";
import { WEEKDAYS, type ExerciseOption, type Plan, type PlanDraft, type PlanEntry, type PlanWeekDay, type Weekday } from "../../api/types";
import { isTimed, planDayEntries, planEntryFromOption, trainingDaysOf } from "../../domain/training";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { bootstrap } from "../../lib/bootstrap";
import { cn } from "../../lib/cn";
import { capitalize, clamp, dateText, isoDay, parseDecimal } from "../../lib/format";
import { Button, IconButton } from "../../ui/Button";
import { Chips, Tag } from "../../ui/Choice";
import { Empty, ErrorNote, Skeleton } from "../../ui/Feedback";
import { TextField, controlClass } from "../../ui/Field";
import { Group, Row, Section } from "../../ui/Layout";
import { Sheet } from "../../ui/Sheet";
import { ExercisePicker } from "./ExercisePicker";

/** Monday of some week: only the weekday names are read from these dates. */
const MONDAY = new Date(2024, 0, 1);

function useWeekdayName(): (key: Weekday) => string {
  const { locale } = useT();
  return (key) => capitalize(dateText(locale, new Date(MONDAY.getFullYear(), 0, 1 + WEEKDAYS.indexOf(key)), { weekday: "long" }));
}

/** One day of a plan: its exercises with sets and repetitions, saved together. */
function DayEditor({ plan, day, status, onClose }: { plan: Plan; day: Weekday; status: PlanWeekDay | undefined; onClose: () => void }) {
  const { t } = useT();
  const text = useServerText();
  const weekday = useWeekdayName();
  const save = useSavePlan();
  const complete = useCompletePlanDay();
  const [entries, setEntries] = useState<PlanEntry[]>(() => planDayEntries(plan, day).map((entry) => ({ ...entry })));
  const [picking, setPicking] = useState(false);
  const [dirty, setDirty] = useState(false);

  const edit = (index: number, patch: Partial<PlanEntry>) => {
    setEntries((list) => list.map((entry, position) => (position === index ? { ...entry, ...patch } : entry)));
    setDirty(true);
  };
  const add = (option: ExerciseOption) => {
    setEntries((list) => [...list, planEntryFromOption(option)]);
    setDirty(true);
  };
  const canComplete = Boolean(status && !status.completed && status.date <= isoDay() && entries.length > 0 && !dirty);

  if (picking) {
    return <ExercisePicker title={t("exercise.add")} taken={new Set(entries.map((entry) => String(entry.exercise.id)))} onPick={add} onClose={() => setPicking(false)} />;
  }

  return (
    <Sheet
      open
      size="lg"
      onClose={onClose}
      title={weekday(day)}
      footer={
        <div className="flex flex-wrap gap-2">
          {canComplete && (
            <Button size="lg" icon={<Check size={18} aria-hidden="true" />} busy={complete.isPending} onClick={() => complete.mutate({ planId: plan.id, day }, { onSuccess: onClose })}>
              {t("workout.markDone")}
            </Button>
          )}
          <Button variant="primary" size="lg" className="flex-1" disabled={!dirty} busy={save.isPending} onClick={() => save.mutate({ id: plan.id, days: { [day]: entries } }, { onSuccess: onClose })}>
            {t("common.save")}
          </Button>
        </div>
      }
    >
      {status?.completed && <p className="mb-3 text-sm text-ink-2">{t("plan.day.completed")}</p>}
      {entries.length === 0 ? (
        <Empty title={t("plan.day.rest")} text={t("plan.day.restText")} />
      ) : (
        <ul className="divide-y divide-rule">
          {entries.map((entry, index) => {
            const timed = isTimed(entry);
            return (
              <li key={`${entry.exercise.id}`} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
                <p className="min-w-0 flex-1 basis-40 font-medium">{text.exercise(entry.exercise.slug, entry.exercise.name)}</p>
                <div className="flex items-center gap-2">
                  <input
                    inputMode="numeric"
                    aria-label={t("plan.sets")}
                    value={entry.sets ?? ""}
                    onChange={(event) => edit(index, { sets: Math.round(clamp(parseDecimal(event.target.value) ?? 1, 1, 20)) })}
                    onFocus={(event) => event.target.select()}
                    className={cn(controlClass, "figure w-14 px-1 text-center")}
                  />
                  <span className="text-muted" aria-hidden="true">
                    ×
                  </span>
                  <input
                    inputMode="numeric"
                    aria-label={timed ? t("set.seconds") : t("set.reps")}
                    value={timed ? (entry.duration_sec ?? "") : (entry.reps ?? "")}
                    onChange={(event) => {
                      const value = Math.round(clamp(parseDecimal(event.target.value) ?? 1, 1, timed ? 3600 : 100));
                      edit(index, timed ? { duration_sec: value } : { reps: String(value) });
                    }}
                    onFocus={(event) => event.target.select()}
                    className={cn(controlClass, "figure w-16 px-1 text-center")}
                  />
                  <span className="w-9 text-sm text-muted">{timed ? t("unit.s") : t("unit.reps")}</span>
                  <IconButton
                    label={t("exercise.removeNamed", { name: text.exercise(entry.exercise.slug, entry.exercise.name) })}
                    onClick={() => {
                      setEntries((list) => list.filter((_, position) => position !== index));
                      setDirty(true);
                    }}
                  >
                    <Trash2 size={18} />
                  </IconButton>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <Button className="mt-3" icon={<Plus size={16} aria-hidden="true" />} onClick={() => setPicking(true)}>
        {t("exercise.add")}
      </Button>
    </Sheet>
  );
}

/** A name is all a new plan needs; the days are filled in afterwards. */
function NewPlanSheet({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const save = useSavePlan();
  const [name, setName] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate({ name: name.trim() || t("plan.defaultName"), active: true, days: {} }, { onSuccess: onClose });
  };
  return (
    <Sheet open onClose={onClose} title={t("plan.new")}>
      <form onSubmit={submit} className="space-y-4">
        <TextField label={t("plan.name")} value={name} onChange={(event) => setName(event.target.value)} placeholder={t("plan.defaultName")} autoFocus autoComplete="off" maxLength={100} hint={t("plan.newHint")} />
        <Button type="submit" variant="primary" size="lg" block busy={save.isPending}>
          {t("plan.create")}
        </Button>
      </form>
    </Sheet>
  );
}

/** Asks the training model for a week, shows it, and saves it as a plan on request. */
function GenerateSheet({ onClose }: { onClose: () => void }) {
  const { t, tn } = useT();
  const weekday = useWeekdayName();
  const generate = useGeneratePlan();
  const save = useSavePlan();
  const [days, setDays] = useState("3");
  const [draft, setDraft] = useState<PlanDraft | null>(null);
  const options = ["2", "3", "4", "5", "6"].map((id) => ({ id, label: id }));
  const filled = draft ? WEEKDAYS.filter((key) => (draft.days[key]?.exercises.length ?? 0) > 0) : [];

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("plan.generate")}
      footer={
        draft ? (
          <Button
            variant="primary"
            size="lg"
            block
            disabled={filled.length === 0}
            busy={save.isPending}
            onClick={() =>
              save.mutate(
                { name: t("plan.generatedName"), active: true, days: Object.fromEntries(filled.map((key) => [key, draft.days[key]?.exercises ?? []])) },
                { onSuccess: onClose },
              )
            }
          >
            {t("plan.saveGenerated")}
          </Button>
        ) : (
          <Button variant="primary" size="lg" block busy={generate.isPending} onClick={() => generate.mutate(Number(days), { onSuccess: setDraft })}>
            {t("plan.generateCta")}
          </Button>
        )
      }
    >
      {draft ? (
        filled.length === 0 ? (
          <Empty title={t("plan.generatedEmpty")} />
        ) : (
          <ul className="divide-y divide-rule">
            {filled.map((key) => (
              <li key={key} className="flex items-baseline justify-between gap-3 py-2.5">
                <span className="font-medium">{weekday(key)}</span>
                <span className="text-sm text-muted">{tn("count.exercises", draft.days[key]?.exercises.length ?? 0)}</span>
              </li>
            ))}
          </ul>
        )
      ) : (
        <div className="space-y-3">
          <p className="text-ink-2">{t("plan.generateText")}</p>
          <Chips wrap label={t("plan.daysPerWeek")} options={options} value={days} onChange={setDays} />
        </div>
      )}
    </Sheet>
  );
}

/** Rename, switch or delete: the rare things, kept one step away from the week. */
function ManageSheet({ plans, active, onClose }: { plans: Plan[]; active: Plan; onClose: () => void }) {
  const { t, tn } = useT();
  const save = useSavePlan();
  const remove = useDeletePlan();
  const [name, setName] = useState(active.name);
  const [confirming, setConfirming] = useState(false);
  const others = plans.filter((plan) => plan.id !== active.id);

  return (
    <Sheet open onClose={onClose} title={t("plan.manage")}>
      <form
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim()) save.mutate({ id: active.id, name: name.trim(), active: true }, { onSuccess: onClose });
        }}
      >
        <TextField className="flex-1" label={t("plan.name")} value={name} onChange={(event) => setName(event.target.value)} maxLength={100} autoComplete="off" />
        <Button type="submit" size="lg" disabled={!name.trim() || name.trim() === active.name} busy={save.isPending}>
          {t("common.save")}
        </Button>
      </form>

      {others.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-sm text-muted">{t("plan.others")}</h3>
          <ul className="-mx-4 divide-y divide-rule border-y border-rule">
            {others.map((plan) => (
              <li key={plan.id}>
                <Row
                  title={plan.name}
                  subtitle={tn("count.trainingDays", trainingDaysOf(plan))}
                  trailing={t("plan.activate")}
                  onClick={() => save.mutate({ id: plan.id, active: true }, { onSuccess: onClose })}
                />
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6">
        {confirming ? (
          <div className="flex gap-2">
            <Button block onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="danger" block busy={remove.isPending} onClick={() => remove.mutate(active.id, { onSuccess: onClose })}>
              {t("plan.deleteConfirm")}
            </Button>
          </div>
        ) : (
          <Button variant="danger" onClick={() => setConfirming(true)}>
            {t("plan.delete")}
          </Button>
        )}
      </div>
    </Sheet>
  );
}

/**
 * The week as seven lines. A day with exercises is a workout, a day without
 * is rest; a tap opens the day to edit it.
 */
export function PlanTab() {
  const { t, tn } = useT();
  const weekday = useWeekdayName();
  const plans = usePlans();
  const save = useSavePlan();
  const list = plans.data ?? [];
  const active = list.find((plan) => plan.is_active) ?? null;
  const week = usePlanWeek(active?.id);
  const [day, setDay] = useState<Weekday | null>(null);
  const [sheet, setSheet] = useState<"new" | "generate" | "manage" | null>(null);
  const canGenerate = bootstrap.features.planGeneration;

  if (plans.isError) return <ErrorNote onRetry={() => void plans.refetch()} />;
  if (plans.isPending) return <Skeleton className="h-72" />;

  const creators = (
    <div className="flex flex-wrap gap-2">
      <Button variant="primary" size="lg" icon={<Plus size={18} aria-hidden="true" />} onClick={() => setSheet("new")}>
        {t("plan.new")}
      </Button>
      {canGenerate && (
        <Button size="lg" icon={<Wand2 size={18} aria-hidden="true" />} onClick={() => setSheet("generate")}>
          {t("plan.generate")}
        </Button>
      )}
    </div>
  );

  return (
    <div data-tone="training" className="max-w-3xl">
      {!active ? (
        <div className="space-y-6">
          <section aria-labelledby="plan-empty">
            <h2 id="plan-empty" className="text-xl">
              {t("plan.empty.title")}
            </h2>
            <p className="mb-4 mt-1.5 max-w-[50ch] text-ink-2">{t("plan.empty.text")}</p>
            {creators}
          </section>
          {list.length > 0 && (
            <Section title={t("plan.saved")}>
              <Group>
                {list.map((plan) => (
                  <Row
                    key={plan.id}
                    title={plan.name}
                    subtitle={tn("count.trainingDays", trainingDaysOf(plan))}
                    trailing={t("plan.activate")}
                    onClick={() => save.mutate({ id: plan.id, active: true })}
                  />
                ))}
              </Group>
            </Section>
          )}
        </div>
      ) : (
        <Section
          title={active.name}
          note={tn("count.trainingDays", trainingDaysOf(active))}
          action={
            <Button variant="quiet" icon={<Settings2 size={16} aria-hidden="true" />} onClick={() => setSheet("manage")}>
              {t("plan.manage")}
            </Button>
          }
        >
          <Group>
            {WEEKDAYS.map((key) => {
              const status = week.data?.days.find((item) => item.key === key);
              const count = planDayEntries(active, key).length;
              return (
                <Row
                  key={key}
                  title={
                    <span className="flex items-center gap-2">
                      {weekday(key)}
                      {status?.is_today && <Tag>{t("plan.today")}</Tag>}
                    </span>
                  }
                  subtitle={count > 0 ? tn("count.exercises", count) : t("plan.rest")}
                  trailing={
                    status?.completed ? (
                      <span className="inline-flex items-center gap-1 text-success">
                        <Check size={16} aria-hidden="true" />
                        {t("plan.done")}
                      </span>
                    ) : undefined
                  }
                  chevron
                  onClick={() => setDay(key)}
                />
              );
            })}
          </Group>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="quiet" icon={<Plus size={16} aria-hidden="true" />} onClick={() => setSheet("new")}>
              {t("plan.another")}
            </Button>
            {canGenerate && (
              <Button variant="quiet" icon={<Wand2 size={16} aria-hidden="true" />} onClick={() => setSheet("generate")}>
                {t("plan.generate")}
              </Button>
            )}
          </div>
        </Section>
      )}

      {active && day && (
        <DayEditor key={`${active.id}:${day}`} plan={active} day={day} status={week.data?.days.find((item) => item.key === day)} onClose={() => setDay(null)} />
      )}
      {sheet === "new" && <NewPlanSheet onClose={() => setSheet(null)} />}
      {sheet === "generate" && <GenerateSheet onClose={() => setSheet(null)} />}
      {sheet === "manage" && active && <ManageSheet plans={list} active={active} onClose={() => setSheet(null)} />}
    </div>
  );
}
