import { useState } from "react";
import { useSetWeight } from "../../api/mutations";
import { useWeight } from "../../api/queries";
import { useT } from "../../i18n";
import { num, parseDecimal } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Stepper } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

const MIN_KG = 20;
const MAX_KG = 400;

/** Today's body weight. It starts from the last weighing, so a small change is two taps. */
export function WeightSheet({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const weight = useWeight();
  const save = useSetWeight();
  const [value, setValue] = useState(() => (weight.data?.weight ? num(weight.data.weight) : ""));
  const parsed = parseDecimal(value);
  const valid = parsed !== null && parsed >= MIN_KG && parsed <= MAX_KG;

  return (
    <Sheet
      open
      onClose={onClose}
      title={t("weight.title")}
      footer={
        <Button variant="primary" size="lg" block disabled={!valid} busy={save.isPending} onClick={() => valid && save.mutate(parsed, { onSuccess: onClose })}>
          {t("common.save")}
        </Button>
      }
    >
      <Stepper label={t("weight.field")} value={value} onChange={setValue} step={0.1} min={MIN_KG} max={MAX_KG} decimals={1} unit={t("unit.kg")} autoFocus />
      <p className="mt-3 text-sm text-muted">{t("weight.hint")}</p>
    </Sheet>
  );
}
