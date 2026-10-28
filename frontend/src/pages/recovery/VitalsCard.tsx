import type { RecoverySnapshot } from "../../api/types";
import { Bar, type BarTone } from "../../components/ui/Bar";
import { Card } from "../../components/ui/Card";
import { Chip, type Tone } from "../../components/ui/Chip";
import { Ring } from "../../components/ui/Ring";
import { useT } from "../../i18n";
import type { TKey } from "../../i18n/en";

interface Level {
  label: TKey;
  tone: Tone;
  bar: BarTone;
}

function levelOf(score: number | null): Level {
  if (score == null) return { label: "rc.level.low", tone: "neutral", bar: "accent" };
  if (score >= 85) return { label: "rc.level.great", tone: "ok", bar: "ok" };
  if (score >= 65) return { label: "rc.level.good", tone: "ok", bar: "ok" };
  if (score >= 40) return { label: "rc.level.fair", tone: "warn", bar: "warn" };
  return { label: "rc.level.low", tone: "danger", bar: "warn" };
}

/** The page's one status card: overall score first, then the four vitals behind it. */
export function VitalsCard({ snapshot }: { snapshot: RecoverySnapshot }) {
  const { t } = useT();
  const score = snapshot.recovery_score;
  const overall = levelOf(score);
  const vitals: Array<{ label: TKey; value: number | null }> = [
    { label: "rc.vital.sleep", value: snapshot.sleep_score },
    { label: "rc.vital.training", value: snapshot.training_score },
    { label: "rc.vital.energy", value: snapshot.energy_score },
    { label: "rc.vital.habits", value: snapshot.habit_score },
  ];

  return (
    <Card
      tone="hero"
      accent="recovery"
      aria-labelledby="vitals-title"
      className="tab:grid tab:grid-cols-[auto_minmax(0,1fr)] tab:items-center tab:gap-x-8"
    >
      <div className="flex items-center gap-5 tab:flex-col tab:gap-3 tab:text-center">
        <Ring
          value={(score ?? 0) / 100}
          size={132}
          stroke={11}
          glow
          from="var(--color-recovery)"
          to="var(--color-ok)"
          label={`${t("rc.score")}: ${score ?? "–"}`}
        >
          <div className="text-4xl font-semibold leading-none tracking-tight tabular-nums">{score ?? "–"}</div>
        </Ring>
        <div className="min-w-0 space-y-2">
          <h2 id="vitals-title" className="text-lg font-semibold leading-tight">
            {t("rc.score")}
          </h2>
          <Chip tone={overall.tone}>{t(overall.label)}</Chip>
        </div>
      </div>

      <ul className="mt-5 grid grid-cols-2 gap-2.5 tab:mt-0">
        {vitals.map(({ label, value }) => {
          const level = levelOf(value);
          return (
            <li key={label} className="space-y-2 rounded-2xl border border-white/8 bg-white/4 p-3">
              <span className="block text-sm font-medium leading-tight text-fg-muted">{t(label)}</span>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-2xl font-semibold leading-none tabular-nums">{value == null ? "–" : `${Math.round(value)}%`}</span>
                <span className="text-xs text-fg-muted">{t(level.label)}</span>
              </div>
              <Bar value={(value ?? 0) / 100} tone={level.bar} label={t(label)} />
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
