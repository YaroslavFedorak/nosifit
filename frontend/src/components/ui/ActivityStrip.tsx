import { CalendarDays } from "lucide-react";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import type { Accent } from "./Card";

export const STRIP_DAYS = 35;

/**
 * The last five weeks as one slim bar: five groups of seven days, oldest on
 * the left. The whole bar is a single 44px+ button that opens the full
 * calendar, so there are no tiny per-day tap targets.
 */
export function ActivityStrip({
  levels,
  accent,
  label,
  summary,
  onOpen,
}: {
  levels: number[];
  accent: Accent;
  label: string;
  summary: string;
  onOpen: () => void;
}) {
  const { t } = useT();
  const padded = [...Array<number>(Math.max(0, STRIP_DAYS - levels.length)).fill(0), ...levels].slice(-STRIP_DAYS);
  const weeks = Array.from({ length: 5 }, (_, week) => padded.slice(week * 7, week * 7 + 7));

  return (
    <button
      type="button"
      data-accent={accent}
      onClick={onOpen}
      aria-label={`${label}. ${summary}. ${t("common.openCalendar")}`}
      className="block min-h-tap w-full rounded-xl text-left transition hover:bg-white/3"
    >
      <span className="mb-2 flex items-center justify-between gap-3 text-xs font-medium text-fg-muted">
        <span>{label}</span>
        <span className="inline-flex items-center gap-1.5 text-accent">
          <CalendarDays size={14} aria-hidden="true" />
          {summary}
        </span>
      </span>
      <span className="flex gap-2.5" aria-hidden="true">
        {weeks.map((week, index) => (
          <span key={index} className="grid flex-1 grid-cols-7 gap-0.5">
            {week.map((level, day) => (
              <span key={day} className={cn("h-6 rounded-[3px]", `lv-${Math.min(4, Math.max(0, level))}`)} />
            ))}
          </span>
        ))}
      </span>
    </button>
  );
}
