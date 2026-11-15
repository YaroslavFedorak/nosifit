import { useState, type FormEvent } from "react";
import { useCreateProduct } from "../../api/mutations";
import type { FoodUnit, Product } from "../../api/types";
import { useT } from "../../i18n";
import { errorCode } from "../../lib/api";
import { parseDecimal } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Chips } from "../../ui/Choice";
import { TextField } from "../../ui/Field";

const amount = (text: string): number | null => {
  if (text.trim() === "") return 0;
  const value = parseDecimal(text);
  return value !== null && value >= 0 ? value : null;
};

/**
 * A product of the user's own: a name, energy, and the three macros for
 * 100 g. Everything else the catalog knows is optional and left out.
 */
export function ProductForm({ initialName = "", barcode, onCreated }: { initialName?: string; barcode?: string; onCreated: (product: Product) => void }) {
  const { t } = useT();
  const create = useCreateProduct();
  const [name, setName] = useState(initialName);
  const [kcal, setKcal] = useState("");
  const [protein, setProtein] = useState("");
  const [fat, setFat] = useState("");
  const [carbs, setCarbs] = useState("");
  const [unit, setUnit] = useState<FoodUnit>("g");
  const [pieceGrams, setPieceGrams] = useState("");
  const [touched, setTouched] = useState(false);

  const values = { kcal: parseDecimal(kcal), protein: amount(protein), fat: amount(fat), carbs: amount(carbs) };
  const piece = unit === "pcs" ? parseDecimal(pieceGrams) : 1;
  const macros = (values.protein ?? 0) + (values.fat ?? 0) + (values.carbs ?? 0);
  const errors = {
    name: name.trim() ? null : t("product.error.name"),
    kcal: values.kcal !== null && values.kcal >= 0 && values.kcal <= 900 ? null : t("product.error.kcal"),
    macros: values.protein !== null && values.fat !== null && values.carbs !== null && macros <= 100 ? null : t("product.error.macros"),
    piece: piece !== null && piece > 0 && piece <= 5000 ? null : t("product.error.piece"),
  };
  const valid = !errors.name && !errors.kcal && !errors.macros && !errors.piece;
  const duplicate = errorCode(create.error) === "duplicate_product";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!valid) return;
    create.mutate(
      {
        name: name.trim(),
        kcal_per_100g: values.kcal ?? 0,
        protein_per_100g: values.protein ?? 0,
        fat_per_100g: values.fat ?? 0,
        carbs_per_100g: values.carbs ?? 0,
        default_unit: unit,
        grams_per_unit: piece ?? 1,
        ...(barcode ? { barcode } : {}),
      },
      { onSuccess: onCreated },
    );
  };

  const per = unit === "ml" ? t("product.per100ml") : t("product.per100g");

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <TextField
        label={t("product.name")}
        value={name}
        onChange={(event) => setName(event.target.value)}
        autoFocus
        autoComplete="off"
        maxLength={120}
        error={duplicate ? t("product.error.duplicate") : touched ? errors.name : null}
      />
      <div>
        <p className="mb-1.5 text-sm font-medium text-ink-2">{t("product.unit")}</p>
        <Chips
          wrap
          label={t("product.unit")}
          value={unit}
          onChange={setUnit}
          options={[
            { id: "g", label: t("product.unit.g") },
            { id: "ml", label: t("product.unit.ml") },
            { id: "pcs", label: t("product.unit.pcs") },
          ]}
        />
      </div>
      {unit === "pcs" && (
        <TextField
          label={t("product.pieceGrams")}
          inputMode="decimal"
          value={pieceGrams}
          onChange={(event) => setPieceGrams(event.target.value)}
          suffix={t("unit.g")}
          error={touched ? errors.piece : null}
        />
      )}
      <TextField
        label={`${t("product.kcal")}, ${per}`}
        inputMode="decimal"
        value={kcal}
        onChange={(event) => setKcal(event.target.value)}
        suffix={t("unit.kcal")}
        error={touched ? errors.kcal : null}
      />
      <fieldset>
        <legend className="mb-1.5 text-sm font-medium text-ink-2">
          {t("product.macros")}, {per}
        </legend>
        <div className="grid grid-cols-3 gap-2">
          <TextField label={t("food.protein")} inputMode="decimal" value={protein} onChange={(event) => setProtein(event.target.value)} suffix={t("unit.g")} />
          <TextField label={t("food.fat")} inputMode="decimal" value={fat} onChange={(event) => setFat(event.target.value)} suffix={t("unit.g")} />
          <TextField label={t("food.carbs")} inputMode="decimal" value={carbs} onChange={(event) => setCarbs(event.target.value)} suffix={t("unit.g")} />
        </div>
        {touched && errors.macros && (
          <p role="alert" className="mt-1 text-sm text-error">
            {errors.macros}
          </p>
        )}
      </fieldset>
      {create.isError && !duplicate && (
        <p role="alert" className="text-sm text-error">
          {t("product.error.save")}
        </p>
      )}
      <Button type="submit" variant="primary" size="lg" block busy={create.isPending}>
        {t("product.create")}
      </Button>
    </form>
  );
}
