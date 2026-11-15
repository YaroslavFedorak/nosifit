import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import type { Tone } from "../design/tokens";
import { useT } from "../i18n";
import { cn } from "../lib/cn";
import { addDays, capitalize, dateText, isoDay, longDay, parseDay } from "../lib/format";
import { IconButton } from "./Button";
import { Sheet } from "./Sheet";

export interface CalendarDay {
  date: string;
  /** 0 (nothing) to 4 (strongest). */
  level: number;
  note?: string;
}

const startOfMonth = (date: Date): Date => new Date(date.getFullYear(), date.getMonth(), 1);

/**
 * The full history one month at a time, with cells big enough to tap. The
 * day under the grid shows `detail` for the picked date when a page gives one.
 */
export function CalendarSheet({
  open,
  onClose,
  title,
  tone,
  days,
  detail,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  tone: Tone;
  days: CalendarDay[];
  detail?: (date: string) => ReactNode;
}) {
  const { t, locale } = useT();
  const today = isoDay();
  const byDate = useMemo(() => new Map(days.map((day) => [day.date, day])), [days]);
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()));
  const [selected, setSelected] = useState<string>(today);

  const earliest = useMemo(() => {
    const first = days
      .filter((day) => day.level > 0)
      .map((day) => day.date)
      .sort()[0];
    return startOfMonth(first ? parseDay(first) : addDays(new Date(), -60));
  }, [days]);
  const latest = startOfMonth(new Date());

  const leading = (cursor.getDay() + 6) % 7;
  const length = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
  const cells: Array<string | null> = [
    ...Array<null>(leading).fill(null),
    ...Array.from({ length }, (_, index) => isoDay(new Date(cursor.getFullYear(), cursor.getMonth(), index + 1))),
  ];
  const weekdays = Array.from({ length: 7 }, (_, index) => capitalize(dateText(locale, new Date(2024, 0, 1 + index), { weekday: "short" })));
  const move = (delta: number) => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1));
  const picked = byDate.get(selected);

  return (
    <Sheet open={open} onClose={onClose} title={title}>
      <div data-tone={tone} className="space-y-4">
        <div className="flex items-center justify-between">
          <IconButton label={t("cal.prev")} disabled={cursor <= earliest} onClick={() => move(-1)}>
            <ChevronLeft size={20} />
          </IconButton>
          <p className="font-medium">{capitalize(dateText(locale, cursor, { month: "long", year: "numeric" }))}</p>
          <IconButton label={t("cal.next")} disabled={cursor >= latest} onClick={() => move(1)}>
            <ChevronRight size={20} />
          </IconButton>
        </div>

        <div className="grid grid-cols-7 gap-1 text-center">
          {weekdays.map((name) => (
            <span key={name} className="pb-1 text-xs text-muted" aria-hidden="true">
              {name}
            </span>
          ))}
          {cells.map((date, index) => {
            if (!date) return <span key={`blank-${index}`} />;
            const level = Math.min(4, Math.max(0, byDate.get(date)?.level ?? 0));
            const isSelected = date === selected;
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={longDay(locale, parseDay(date))}
                disabled={date > today}
                onClick={() => setSelected(date)}
                className={cn(
                  "figure relative grid aspect-square min-h-10 place-items-center rounded-control text-sm font-medium disabled:cursor-not-allowed disabled:opacity-40",
                  `lv-${level}`,
                  level >= 3 ? "text-paper" : "text-ink",
                  isSelected && "outline-2 outline-offset-1 outline-ink",
                )}
              >
                {Number(date.slice(8))}
                {date === today && <span className="absolute bottom-1 h-0.5 w-3 rounded-pill bg-current" aria-hidden="true" />}
              </button>
            );
          })}
        </div>

        <div aria-live="polite" className="border-t border-rule pt-3">
          <p className="font-medium">{longDay(locale, parseDay(selected))}</p>
          {detail ? <div className="mt-2">{detail(selected)}</div> : <p className="mt-0.5 text-sm text-muted">{picked?.note ?? t("cal.none")}</p>}
        </div>
      </div>
    </Sheet>
  );
}
