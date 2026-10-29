import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { addDays, capitalize, dateText, isoDay, parseDay } from "../../lib/format";
import { IconButton } from "./Button";
import type { Accent } from "./Card";
import { Sheet } from "./Sheet";

export interface CalendarDay {
  date: string;
  /** 0 (nothing) to 4 (strongest). */
  level: number;
  note?: string;
}

const startOfMonth = (date: Date): Date => new Date(date.getFullYear(), date.getMonth(), 1);

/**
 * The full history, one month at a time, with cells big enough to tap.
 * Replaces the year-wide grid that scrolled sideways inside a card.
 */
export function CalendarSheet({
  open,
  onClose,
  title,
  accent,
  days,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  accent: Accent;
  days: CalendarDay[];
}) {
  const { t, locale } = useT();
  const today = isoDay();
  const byDate = useMemo(() => new Map(days.map((day) => [day.date, day])), [days]);
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()));
  const [selected, setSelected] = useState<string>(today);

  const earliest = useMemo(() => {
    const first = days.map((day) => day.date).sort()[0];
    return startOfMonth(first ? parseDay(first) : addDays(new Date(), -120));
  }, [days]);
  const latest = startOfMonth(new Date());

  const monthStart = cursor;
  const leading = (monthStart.getDay() + 6) % 7;
  const length = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
  const cells: Array<string | null> = [
    ...Array<null>(leading).fill(null),
    ...Array.from({ length }, (_, index) => isoDay(new Date(monthStart.getFullYear(), monthStart.getMonth(), index + 1))),
  ];
  const weekdays = Array.from({ length: 7 }, (_, index) =>
    dateText(locale, new Date(2024, 0, 1 + index), { weekday: "short" }),
  );
  const move = (delta: number) => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1));
  const picked = byDate.get(selected);

  return (
    <Sheet open={open} onClose={onClose} title={title}>
      <div data-accent={accent} className="space-y-4">
        <div className="flex items-center justify-between">
          <IconButton label={t("cal.prev")} disabled={cursor <= earliest} onClick={() => move(-1)}>
            <ChevronLeft size={20} />
          </IconButton>
          <p className="text-base font-semibold">{capitalize(dateText(locale, cursor, { month: "long", year: "numeric" }))}</p>
          <IconButton label={t("cal.next")} disabled={cursor >= latest} onClick={() => move(1)}>
            <ChevronRight size={20} />
          </IconButton>
        </div>

        <div className="grid grid-cols-7 gap-1.5 text-center">
          {weekdays.map((name) => (
            <span key={name} className="pb-1 text-xs font-medium text-fg-soft">
              {name}
            </span>
          ))}
          {cells.map((date, index) => {
            if (!date) return <span key={`blank-${index}`} />;
            const level = byDate.get(date)?.level ?? 0;
            const isSelected = date === selected;
            return (
              <button
                key={date}
                type="button"
                aria-pressed={isSelected}
                aria-label={dateText(locale, parseDay(date), { weekday: "long", day: "numeric", month: "long" })}
                onClick={() => setSelected(date)}
                className={cn(
                  "relative grid aspect-square min-h-tap place-items-center rounded-xl text-sm font-medium transition",
                  `lv-${Math.min(4, Math.max(0, level))}`,
                  level >= 3 ? "text-canvas" : "text-fg",
                  isSelected && "ring-2 ring-fg",
                  date > today && "opacity-40",
                )}
              >
                {Number(date.slice(8))}
                {date === today && <span className="absolute bottom-1 size-1 rounded-full bg-current" aria-hidden="true" />}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-end gap-1.5 text-xs text-fg-muted" aria-hidden="true">
          <span>{t("cal.less")}</span>
          {[0, 1, 2, 3, 4].map((level) => (
            <span key={level} className={cn("size-3.5 rounded-[4px]", `lv-${level}`)} />
          ))}
          <span>{t("cal.more")}</span>
        </div>

        <div aria-live="polite" className="rounded-xl border border-line bg-surface-2 p-3 text-sm">
          <p className="font-semibold">{capitalize(dateText(locale, parseDay(selected), { weekday: "long", day: "numeric", month: "long" }))}</p>
          <p className="mt-0.5 text-fg-muted">{picked?.note ?? t("cal.none")}</p>
        </div>
      </div>
    </Sheet>
  );
}
