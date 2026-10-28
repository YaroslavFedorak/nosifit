import { Lightbulb } from "lucide-react";
import { useState } from "react";
import { useTrainingRecommendations } from "../../api/queries";
import type { GuidanceItem, RecommendedExercise } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Chip } from "../../components/ui/Chip";
import { EmptyState, ErrorState, Skeleton } from "../../components/ui/States";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { num } from "../../lib/format";

/** One column on a phone, two or more where the card is wide enough. */
const TIP_GRID = "mt-3 grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-2.5";

export function GuidanceCard({ item, tone }: { item: GuidanceItem; tone: "accent" | "warn" }) {
  const text = useServerText();
  const action = text.text(item.action, item.params);
  const reasons = item.reasons.map((reason) => text.text(reason, item.params)).filter(Boolean).slice(0, 2);
  return (
    <li className="rounded-xl border border-line bg-surface-2/50 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold">{text.muscle(item.muscle)}</h3>
        {action && <Chip tone={tone}>{action}</Chip>}
      </div>
      {reasons.length > 0 && <p className="mt-1.5 text-sm text-fg-muted">{reasons.join(" · ")}</p>}
    </li>
  );
}

export function ExerciseTip({ item }: { item: RecommendedExercise }) {
  const { t } = useT();
  const text = useServerText();
  const prescription = item.duration_sec
    ? `${item.sets ?? 1} × ${num(item.duration_sec, 0)} ${t("unit.s")}`
    : t("tr.tips.prescription", { sets: item.sets ?? 3, reps: item.reps ?? "–" });
  const reason = text.text(item.reasons[0]);
  return (
    <li className="rounded-xl border border-line bg-surface-2/50 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 text-base font-semibold leading-snug">{text.exercise(item.slug, item.exercise)}</h3>
        <span className="shrink-0 pt-0.5 text-sm font-semibold tabular-nums text-accent">{prescription}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {item.target_muscles.map((muscle) => (
          <Chip key={muscle}>{text.muscle(muscle)}</Chip>
        ))}
      </div>
      {reason && <p className="mt-2 text-sm text-fg-muted">{reason}</p>}
    </li>
  );
}

/** One focus muscle and three exercises up front; the rest opens on request. */
export function TipsTab() {
  const { t } = useT();
  const text = useServerText();
  const recommendations = useTrainingRecommendations();
  const [moreGuidance, setMoreGuidance] = useState(false);
  const [moreExercises, setMoreExercises] = useState(false);

  if (recommendations.isError) return <ErrorState onRetry={() => void recommendations.refetch()} />;
  if (recommendations.isPending || !text.ready) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-40" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  const focus = recommendations.data.guidance?.muscles ?? [];
  const rest = recommendations.data.guidance?.warnings ?? [];
  const exercises = recommendations.data.recommended_exercises ?? [];

  if (focus.length === 0 && exercises.length === 0) {
    return (
      <Card>
        <EmptyState icon={<Lightbulb size={22} />} title={t("tr.tips.empty")} />
      </Card>
    );
  }

  return (
    <div className="grid gap-4 desk:grid-cols-2 desk:items-start" data-accent="training">
      {focus.length > 0 && (
        <Card accent="training" aria-labelledby="focus-title">
          <h2 id="focus-title" className="text-base font-semibold">
            {t("tr.tips.focus")}
          </h2>
          <ul className={TIP_GRID}>
            {(moreGuidance ? focus : focus.slice(0, 1)).map((item) => (
              <GuidanceCard key={item.muscle} item={item} tone="accent" />
            ))}
          </ul>
          {moreGuidance && rest.length > 0 && (
            <>
              <h3 className="mt-5 text-sm font-semibold text-fg-muted">{t("tr.tips.rest")}</h3>
              <ul className={TIP_GRID}>
                {rest.map((item) => (
                  <GuidanceCard key={item.muscle} item={item} tone="warn" />
                ))}
              </ul>
            </>
          )}
          {(focus.length > 1 || rest.length > 0) && (
            <Button variant="ghost" block className="mt-3" aria-expanded={moreGuidance} onClick={() => setMoreGuidance((open) => !open)}>
              {moreGuidance ? t("common.showLess") : t("common.showMore")}
            </Button>
          )}
        </Card>
      )}

      {exercises.length > 0 && (
        <Card accent="training" aria-labelledby="exercises-title">
          <h2 id="exercises-title" className="text-base font-semibold">
            {t("tr.tips.exercises")}
          </h2>
          <ul className={TIP_GRID}>
            {(moreExercises ? exercises : exercises.slice(0, 3)).map((item) => (
              <ExerciseTip key={item.slug ?? item.exercise} item={item} />
            ))}
          </ul>
          {exercises.length > 3 && (
            <Button variant="ghost" block className="mt-3" aria-expanded={moreExercises} onClick={() => setMoreExercises((open) => !open)}>
              {moreExercises ? t("common.showLess") : t("common.showMore")}
            </Button>
          )}
        </Card>
      )}
    </div>
  );
}
