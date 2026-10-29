import { Check, ScanBarcode, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useLogFood } from "../../api/mutations";
import { useProducts } from "../../api/queries";
import { MEAL_CATEGORIES, type MealCategory, type Product, type ProductSource } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Sheet } from "../../components/ui/Sheet";
import { EmptyState, Skeleton } from "../../components/ui/States";
import { parseDecimal, Stepper } from "../../components/ui/Stepper";
import { Tabs, type TabItem } from "../../components/ui/Tabs";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { clamp, num } from "../../lib/format";
import { toast } from "../../lib/toast";
import { useDebounced } from "../../lib/useDebounced";
import { unitLabel } from "./MealsCard";

/**
 * Pick a food, set the portion, add it to a meal. The four sources are
 * laid out 2 × 2 on a phone so their full names always fit.
 */
export function ProductSheet({ open, onClose, initialCategory }: { open: boolean; onClose: () => void; initialCategory: MealCategory }) {
  const { t } = useT();
  const log = useLogFood();
  const [category, setCategory] = useState<MealCategory>(initialCategory);
  const [source, setSource] = useState<ProductSource>("all");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Product | null>(null);
  const [amount, setAmount] = useState("100");
  const search = useDebounced(query.trim());
  const products = useProducts(source, search, open);

  const visible = useMemo(() => {
    const list = products.data ?? [];
    if (source === "all" || !search) return list;
    const needle = search.toLowerCase();
    return list.filter((product) => product.name.toLowerCase().includes(needle));
  }, [products.data, source, search]);

  const amountValue = parseDecimal(amount);
  const ready = picked !== null && amountValue !== null && amountValue > 0;
  const portionKcal = picked && amountValue ? (picked.kcal_per_100g * amountValue) / 100 : null;

  const sources: TabItem<ProductSource>[] = [
    { id: "all", label: t("nu.tab.all") },
    { id: "fav", label: t("nu.tab.fav") },
    { id: "recent", label: t("nu.tab.recent") },
    { id: "mine", label: t("nu.tab.mine") },
  ];
  const categories: TabItem<MealCategory>[] = MEAL_CATEGORIES.map((id) => ({ id, label: t(`nu.meal.${id}` as "nu.meal.breakfast") }));

  const add = () => {
    if (!picked || !amountValue) return;
    log.mutate(
      { category, productId: picked.id, amount: clamp(amountValue, 1, 5000), unit: picked.default_unit || "g" },
      {
        onSuccess: () => {
          toast(t("common.saved"));
          onClose();
        },
      },
    );
  };

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={t("nu.sheet.title")}
      footer={
        picked ? (
          <div className="space-y-3">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Stepper
                  label={`${t("nu.item.amount")}, ${unitLabel(picked.default_unit || "g", t)}`}
                  value={amount}
                  onChange={setAmount}
                  step={10}
                  min={1}
                  max={5000}
                />
              </div>
              {portionKcal !== null && (
                <p className="pb-3 text-sm font-semibold tabular-nums text-fg-muted">
                  {num(portionKcal, 0)} {t("unit.kcal")}
                </p>
              )}
            </div>
            <Button variant="primary" size="lg" block disabled={!ready || log.isPending} onClick={add}>
              {t("nu.addTo", { meal: t(`nu.meal.${category}` as "nu.meal.breakfast") })}
            </Button>
          </div>
        ) : (
          <p className="py-2 text-center text-sm text-fg-muted">{t("nu.pick")}</p>
        )
      }
    >
      <div className="space-y-3 pt-1">
        <Tabs items={categories} value={category} onChange={setCategory} label={t("nu.meal")} />
        <Tabs items={sources} value={source} onChange={setSource} label={t("nu.tabs")} twoRows />
        <label className="relative block">
          <span className="sr-only">{t("nu.search")}</span>
          <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-soft" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("nu.search")}
            autoComplete="off"
            className="min-h-tap-lg w-full rounded-xl border border-line-strong bg-surface-2 pl-10 pr-3 text-base outline-none placeholder:text-fg-soft focus:border-fg/40"
          />
        </label>
        <a
          href="/nutrition/"
          className="inline-flex min-h-tap items-center gap-2 rounded-xl px-1 text-sm font-medium text-nutrition hover:text-fg"
        >
          <ScanBarcode size={18} aria-hidden="true" />
          {t("nu.scan")}
        </a>

        {products.isPending ? (
          <div className="space-y-2">
            {[0, 1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-14" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <EmptyState icon={<Search size={22} />} title={t("nu.empty")} />
        ) : (
          <ul className="space-y-1.5 pb-2">
            {visible.map((product) => {
              const selected = picked?.id === product.id;
              return (
                <li key={product.id}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => {
                      setPicked(product);
                      if (product.id !== picked?.id) setAmount("100");
                    }}
                    className={cn(
                      "flex min-h-14 w-full items-center justify-between gap-3 rounded-xl border px-3.5 py-2 text-left transition active:scale-[0.99]",
                      selected ? "border-nutrition/60 bg-nutrition/10" : "border-line bg-surface-2/50 hover:bg-surface-2",
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold leading-snug">{product.name}</span>
                      <span className="block text-xs text-fg-muted">
                        {product.brand ? `${product.brand}, ` : ""}
                        {num(product.kcal_per_100g, 0)} {t("unit.kcal")} {t("nu.per100")}
                      </span>
                    </span>
                    {selected && <Check size={18} className="shrink-0 text-nutrition" aria-hidden="true" />}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Sheet>
  );
}
