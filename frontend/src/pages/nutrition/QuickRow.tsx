import { useState } from "react";
import { useAddWater, useSetWeight } from "../../api/mutations";
import { useWater, useWeight } from "../../api/queries";
import { Bar } from "../../components/ui/Bar";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Sheet } from "../../components/ui/Sheet";
import { parseDecimal, Stepper } from "../../components/ui/Stepper";
import { useT } from "../../i18n";
import { clamp, num, ratio } from "../../lib/format";
import { toast } from "../../lib/toast";

const WATER_STEPS = [0.25, 0.5, 1, -0.25];

function WeightSheet({ current, onClose }: { current: number | null; onClose: () => void }) {
  const { t } = useT();
  const setWeight = useSetWeight();
  const [value, setValue] = useState(current ? num(current) : "");
  const parsed = parseDecimal(value);
  const valid = parsed !== null && parsed >= 20 && parsed <= 400;

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("nu.weight.title")}
      footer={
        <Button
          variant="primary"
          size="lg"
          block
          disabled={!valid || setWeight.isPending}
          onClick={() =>
            valid &&
            setWeight.mutate(clamp(parsed, 20, 400), {
              onSuccess: () => {
                toast(t("common.saved"));
                onClose();
              },
            })
          }
        >
          {t("common.save")}
        </Button>
      }
    >
      <div className="pt-2">
        <Stepper label={t("nu.weight.field")} value={value} onChange={setValue} step={0.1} min={20} max={400} decimals={1} />
      </div>
    </Sheet>
  );
}

/** Water with its one-tap amounts, and the body weight as one row under it. */
export function QuickRow() {
  const { t } = useT();
  const water = useWater();
  const weight = useWeight();
  const addWater = useAddWater();
  const [weightOpen, setWeightOpen] = useState(false);
  const liters = water.data?.amount ?? 0;
  const goal = water.data?.recommended ?? null;

  return (
    <div className="space-y-3">
      <Card data-accent="water" aria-labelledby="water-title" className="space-y-3">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h2 id="water-title" className="text-sm font-medium text-fg-muted">
              {t("nu.water")}
            </h2>
            <p className="mt-1 text-2xl font-semibold leading-none tabular-nums">
              {num(liters)} <span className="text-sm font-medium text-fg-muted">{t("unit.l")}</span>
            </p>
          </div>
          {goal ? <p className="text-sm text-fg-muted">{t("nu.waterOf", { n: num(goal) })}</p> : null}
        </div>
        {goal ? <Bar value={ratio(liters, goal)} tone="water" label={t("nu.water")} /> : null}
        <div className="grid grid-cols-4 gap-2">
          {WATER_STEPS.map((step) => (
            <button
              key={step}
              type="button"
              disabled={addWater.isPending || (step < 0 && liters <= 0)}
              onClick={() => addWater.mutate(step)}
              className="min-h-tap rounded-xl border border-line-strong bg-surface-2 text-sm font-semibold tabular-nums transition hover:bg-surface-3 active:scale-95 disabled:opacity-40"
            >
              {step > 0 ? "+" : "−"}
              {num(Math.abs(step), 2)}
            </button>
          ))}
        </div>
      </Card>

      <Card aria-labelledby="weight-title" className="flex items-center justify-between gap-3">
        <div>
          <h2 id="weight-title" className="text-sm font-medium text-fg-muted">
            {t("nu.weight")}
          </h2>
          <p className="mt-1 text-2xl font-semibold leading-none tabular-nums">
            {weight.data?.weight ? num(weight.data.weight) : "–"}{" "}
            <span className="text-sm font-medium text-fg-muted">{t("unit.kg")}</span>
          </p>
        </div>
        <Button onClick={() => setWeightOpen(true)}>
          {t("nu.weight.update")}
        </Button>
      </Card>

      {weightOpen && <WeightSheet current={weight.data?.weight ?? null} onClose={() => setWeightOpen(false)} />}
    </div>
  );
}
