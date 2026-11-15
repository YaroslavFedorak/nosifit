import { useState } from "react";
import { useDeleteEntry, useUpdateEntry } from "../../api/mutations";
import type { MealItem } from "../../api/types";
import { MAX_AMOUNT, amountStep } from "../../domain/nutrition";
import { useT } from "../../i18n";
import { clamp, num, parseDecimal } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Stepper } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";
import { unitLabel } from "./FoodPicker";

/** Changes the amount of a logged food, or removes it. */
export function EntrySheet({ item, onClose }: { item: MealItem; onClose: () => void }) {
  const { t } = useT();
  const update = useUpdateEntry();
  const remove = useDeleteEntry();
  const [amount, setAmount] = useState(num(item.amount));
  const parsed = parseDecimal(amount);
  const valid = parsed !== null && parsed > 0 && parsed <= MAX_AMOUNT;
  const busy = update.isPending || remove.isPending;
  // The entry keeps the values it was logged with, so the new figure scales from them.
  const kcal = valid && item.amount > 0 ? (item.calories / item.amount) * parsed : null;

  return (
    <Sheet
      open
      onClose={onClose}
      title={item.name}
      footer={
        <div className="flex gap-2">
          <Button variant="danger" size="lg" disabled={busy} onClick={() => remove.mutate(item.id, { onSuccess: onClose })}>
            {t("common.remove")}
          </Button>
          <Button
            variant="primary"
            size="lg"
            className="flex-1"
            disabled={!valid || busy}
            busy={update.isPending}
            onClick={() => valid && update.mutate({ id: item.id, amount: clamp(parsed, 0.1, MAX_AMOUNT), unit: item.unit }, { onSuccess: onClose })}
          >
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <Stepper
        label={`${t("food.amount")}, ${unitLabel(item.unit, t)}`}
        value={amount}
        onChange={setAmount}
        step={amountStep(item.unit)}
        min={item.unit === "pcs" ? 0.5 : 1}
        max={MAX_AMOUNT}
        decimals={item.unit === "pcs" ? 1 : 0}
        autoFocus
      />
      <p className="mt-3 text-sm text-muted" aria-live="polite">
        {kcal !== null ? `${num(kcal, 0)} ${t("unit.kcal")}` : t("food.amountInvalid")}
      </p>
    </Sheet>
  );
}
