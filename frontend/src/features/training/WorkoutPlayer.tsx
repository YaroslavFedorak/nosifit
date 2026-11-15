import { ChevronLeft, ChevronRight, Pause, Play, Plus, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import type { ExerciseOption, LoggedExercise, SetEntry } from "../../api/types";
import { entriesOf, exerciseFromOption, isTimed, totalSets, totalVolume, withEntries } from "../../domain/training";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { cn } from "../../lib/cn";
import { clamp, clock, num, parseDecimal } from "../../lib/format";
import { Button, IconButton } from "../../ui/Button";
import { Tick } from "../../ui/Choice";
import { Stepper } from "../../ui/Field";
import { Stat } from "../../ui/Layout";
import { Sheet } from "../../ui/Sheet";
import { ExercisePicker } from "./ExercisePicker";
import { setLabel } from "./useWorkout";

export interface PlayerItem {
  exercise: LoggedExercise;
  /** How many of its sets are confirmed. Only those are saved. */
  done: number;
}

/** The workout as it stands: every exercise with the sets confirmed so far. */
const confirmed = (items: PlayerItem[]): LoggedExercise[] =>
  items.filter((item) => item.done > 0).map((item) => withEntries(item.exercise, entriesOf(item.exercise).slice(0, item.done)));

/** Counts a timed set down. The count is an aid: the set is confirmed by hand. */
function Countdown({ seconds }: { seconds: number }) {
  const { t } = useT();
  const [left, setLeft] = useState(seconds);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    setLeft(seconds);
    setRunning(false);
  }, [seconds]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      setLeft((value) => {
        if (value > 1) return value - 1;
        setRunning(false);
        navigator.vibrate?.(200);
        return 0;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running]);

  return (
    <div className="flex items-center justify-between gap-3 rounded-card bg-paper-3 px-4 py-3">
      <p className="figure text-3xl" role="timer" aria-live="off">
        {clock(left)}
      </p>
      <div className="flex gap-2">
        <IconButton tonal label={t("player.reset")} onClick={() => { setLeft(seconds); setRunning(false); }}>
          <RotateCcw size={18} />
        </IconButton>
        <Button icon={running ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />} disabled={left === 0} onClick={() => setRunning((value) => !value)}>
          {running ? t("player.pause") : t("player.start")}
        </Button>
      </div>
    </div>
  );
}

/**
 * A workout one set at a time: the current exercise, the current set, one
 * button to confirm it. Every confirmed set is saved at once, so leaving
 * half-way keeps exactly what was done.
 */
export function WorkoutPlayer({
  initial,
  persist,
  busy,
  onClose,
}: {
  initial: PlayerItem[];
  persist: (exercises: LoggedExercise[]) => Promise<void>;
  busy: boolean;
  onClose: () => void;
}) {
  const { t } = useT();
  const text = useServerText();
  const [items, setItems] = useState<PlayerItem[]>(initial);
  const [index, setIndex] = useState(() => Math.max(0, initial.findIndex((item) => item.done < entriesOf(item.exercise).length)));
  const [finished, setFinished] = useState(false);
  const [picking, setPicking] = useState(initial.length === 0);

  const item = items[index];
  const entries = item ? entriesOf(item.exercise) : [];
  const timed = item ? isTimed(item.exercise) : false;
  const current: SetEntry | undefined = item ? entries[item.done] : undefined;
  const [amount, setAmount] = useState("");
  const [load, setLoad] = useState("");

  // The fields follow the set in hand: its planned values, ready to be corrected.
  const setKey = `${index}:${item?.done ?? 0}:${entries.length}`;
  useEffect(() => {
    if (!current) return;
    setAmount(num(timed ? (current.duration_sec ?? 30) : (current.reps ?? 10), 0));
    setLoad(current.load ? num(current.load) : "0");
    // The key names the set; its values are read when it changes.
  }, [setKey]);

  const done = confirmed(items);

  const confirm = async () => {
    if (!item || !current) return;
    const weight = clamp(parseDecimal(load) ?? 0, 0, 2000);
    const entry: SetEntry = timed
      ? { duration_sec: Math.round(clamp(parseDecimal(amount) ?? 30, 1, 3600)), load: weight }
      : { reps: Math.round(clamp(parseDecimal(amount) ?? 10, 1, 100)), load: weight };
    const nextEntries = entries.map((existing, position) => (position === item.done ? entry : existing));
    const next = items.map((existing, position) =>
      position === index ? { exercise: withEntries(existing.exercise, nextEntries), done: existing.done + 1 } : existing,
    );
    setItems(next);
    try {
      await persist(confirmed(next));
    } catch {
      // The save failed and said so: the set goes back to being unconfirmed.
      setItems(items);
    }
  };

  const addSet = () => {
    if (!item) return;
    const last = entries[entries.length - 1] ?? (timed ? { duration_sec: 30, load: 0 } : { reps: 10, load: 0 });
    setItems(items.map((existing, position) => (position === index ? { ...existing, exercise: withEntries(existing.exercise, [...entries, { ...last }]) } : existing)));
  };

  const addExercise = (option: ExerciseOption) => {
    setItems((list) => [...list, { exercise: exerciseFromOption(option), done: 0 }]);
    setIndex(items.length);
    setPicking(false);
  };

  const isLast = index >= items.length - 1;
  const name = item ? text.exercise(item.exercise.slug, item.exercise.name) : "";

  if (picking) {
    return (
      <ExercisePicker
        title={t("exercise.add")}
        taken={new Set(items.map((entry) => entry.exercise.id))}
        onPick={addExercise}
        onClose={() => (items.length === 0 ? onClose() : setPicking(false))}
      />
    );
  }

  if (finished || !item) {
    return (
      <Sheet
        open
        onClose={onClose}
        title={t("player.finished")}
        footer={
          <Button variant="primary" size="lg" block onClick={onClose}>
            {t("common.done")}
          </Button>
        }
      >
        {done.length > 0 ? (
          <div className="grid grid-cols-3 gap-4 py-2">
            <Stat value={done.length} label={t("workout.exercises")} />
            <Stat value={totalSets(done)} label={t("workout.sets")} />
            <Stat value={num(totalVolume(done), 0)} unit={t("unit.kg")} label={t("workout.volume")} />
          </div>
        ) : (
          <p className="py-2 text-ink-2">{t("player.nothing")}</p>
        )}
      </Sheet>
    );
  }

  return (
    <Sheet
      open
      size="tall"
      onClose={onClose}
      title={t("player.title")}
      footer={
        <div className="flex items-center gap-2">
          <IconButton tonal label={t("player.prev")} disabled={index === 0} onClick={() => setIndex(index - 1)}>
            <ChevronLeft size={20} />
          </IconButton>
          <IconButton tonal label={t("player.next")} disabled={isLast} onClick={() => setIndex(index + 1)}>
            <ChevronRight size={20} />
          </IconButton>
          <Button variant="quiet" icon={<Plus size={16} aria-hidden="true" />} onClick={() => setPicking(true)}>
            {t("exercise.add")}
          </Button>
          <Button className="ml-auto" onClick={() => setFinished(true)}>
            {t("player.finish")}
          </Button>
        </div>
      }
    >
      <div data-tone="training" className="flex min-h-full flex-col gap-4">
        <div>
          <div className="flex gap-1" aria-hidden="true">
            {items.map((entry, position) => (
              <span
                key={entry.exercise.id}
                className={cn(
                  "h-1 flex-1 rounded-pill",
                  entry.done >= entriesOf(entry.exercise).length ? "bg-tone" : position === index ? "bg-tone opacity-50" : "bg-paper-4",
                )}
              />
            ))}
          </div>
          <p className="mt-3 text-sm text-muted">{t("player.position", { n: index + 1, total: items.length })}</p>
          <h3 className="mt-1 text-xl">{name}</h3>
        </div>

        {current ? (
          <>
            <p className="text-ink-2" aria-live="polite">
              {t("player.set", { n: item.done + 1, total: entries.length })}
              {item.exercise.per_side ? `, ${t("player.perSide")}` : ""}
            </p>
            <div className={cn("grid gap-3", item.exercise.accepts_load !== false && "grid-cols-2")}>
              <Stepper
                label={timed ? t("set.seconds") : t("set.reps")}
                value={amount}
                onChange={setAmount}
                step={timed ? 5 : 1}
                min={1}
                max={timed ? 3600 : 100}
              />
              {item.exercise.accepts_load !== false && (
                <Stepper label={t("set.load")} value={load} onChange={setLoad} step={2.5} min={0} max={2000} decimals={1} />
              )}
            </div>
            {timed && <Countdown seconds={Math.round(clamp(parseDecimal(amount) ?? 30, 1, 3600))} />}
            <Button variant="primary" size="lg" block busy={busy} onClick={() => void confirm()}>
              {t("player.confirm")}
            </Button>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-ink-2" aria-live="polite">
              {t("player.allDone")}
            </p>
            <div className="flex flex-wrap gap-2">
              {isLast ? (
                <Button variant="primary" size="lg" onClick={() => setFinished(true)}>
                  {t("player.finish")}
                </Button>
              ) : (
                <Button variant="primary" size="lg" icon={<ChevronRight size={18} aria-hidden="true" />} onClick={() => setIndex(index + 1)}>
                  {t("player.nextExercise")}
                </Button>
              )}
              <Button size="lg" onClick={addSet}>
                {t("player.oneMore")}
              </Button>
            </div>
          </div>
        )}

        <ul className="mt-auto divide-y divide-rule border-t border-rule">
          {entries.map((entry, position) => (
            <li key={position} className="flex min-h-11 items-center gap-3 py-2">
              <Tick checked={position < item.done} />
              <span className={cn("figure flex-1 text-sm font-normal", position < item.done ? "text-muted" : position === item.done ? "text-ink" : "text-ink-2")}>
                {t("set.n", { n: position + 1 })}: {setLabel(entry, timed, t)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </Sheet>
  );
}
