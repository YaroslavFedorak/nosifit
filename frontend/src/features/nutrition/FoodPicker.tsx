import { Check, Plus, ScanBarcode, Search, Star, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useDeleteDish, useDeleteProduct, useFavorite, useLogFood } from "../../api/mutations";
import { useDishes, useProducts, type ProductSource } from "../../api/queries";
import { MEAL_CATEGORIES, type Dish, type FoodUnit, type MealCategory, type Product } from "../../api/types";
import { MAX_AMOUNT, amountStep, defaultAmount, mealForNow, portionOf } from "../../domain/nutrition";
import { useT, type I18n } from "../../i18n";
import { cn } from "../../lib/cn";
import { clamp, num, parseDecimal } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { Button, IconButton } from "../../ui/Button";
import { Chips, type Option } from "../../ui/Choice";
import { Empty, SkeletonRows } from "../../ui/Feedback";
import { Stepper, controlClass } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";
import { BarcodeScanner } from "./BarcodeScanner";
import { ProductForm } from "./ProductForm";

export function unitLabel(unit: string, t: I18n["t"]): string {
  return unit === "g" ? t("unit.g") : unit === "ml" ? t("unit.ml") : unit === "pcs" ? t("unit.pcs") : unit;
}

type Shelf = Exclude<ProductSource, "search"> | "dishes";

type View =
  | { name: "list" }
  | { name: "portion"; product: Product }
  | { name: "dish"; dish: Dish }
  | { name: "create"; barcode?: string; initialName?: string }
  | { name: "scan" };

const QUICK_AMOUNTS: Record<FoodUnit, number[]> = { g: [50, 100, 150, 200, 300], ml: [100, 200, 250, 330, 500], pcs: [1, 2, 3, 4] };

/** Sets the amount of one product and adds it. The figure updates as the amount changes. */
function PortionView({
  product,
  mealName,
  busy,
  onAdd,
  onDeleted,
}: {
  product: Product;
  mealName: string;
  busy: boolean;
  onAdd: (amount: number, unit: FoodUnit) => void;
  onDeleted: () => void;
}) {
  const { t } = useT();
  const favorite = useFavorite();
  const remove = useDeleteProduct();
  const [unit, setUnit] = useState<FoodUnit>(product.default_unit);
  const [amount, setAmount] = useState(String(defaultAmount(product.default_unit)));
  const [starred, setStarred] = useState(product.is_favorite);
  const [confirming, setConfirming] = useState(false);
  const parsed = parseDecimal(amount);
  const valid = parsed !== null && parsed > 0 && parsed <= MAX_AMOUNT;
  const portion = valid ? portionOf(product, parsed, unit) : null;
  const units: Option<FoodUnit>[] =
    product.default_unit === "g"
      ? []
      : [
          { id: product.default_unit, label: unitLabel(product.default_unit, t) },
          { id: "g", label: unitLabel("g", t) },
        ];

  return (
    <div className="flex h-full flex-col gap-4" data-tone="nutrition">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-muted">
          {product.brand ? `${product.brand}, ` : ""}
          {num(product.kcal_per_100g, 0)} {t("unit.kcal")} {t("food.per100")}
        </p>
        <IconButton
          label={starred ? t("food.unfavorite") : t("food.favorite")}
          aria-pressed={starred}
          onClick={() => {
            setStarred(!starred);
            favorite.mutate({ id: product.id, favorite: !starred }, { onError: () => setStarred(starred) });
          }}
          className="-mr-2 -mt-2"
        >
          <Star size={20} className={starred ? "fill-accent text-accent" : undefined} />
        </IconButton>
      </div>

      <Stepper
        label={`${t("food.amount")}, ${unitLabel(unit, t)}`}
        value={amount}
        onChange={setAmount}
        step={amountStep(unit)}
        min={unit === "pcs" ? 0.5 : 1}
        max={MAX_AMOUNT}
        decimals={unit === "pcs" ? 1 : 0}
        autoFocus
      />
      <div className="flex flex-wrap gap-2">
        {QUICK_AMOUNTS[unit].map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setAmount(String(value))}
            className={cn(
              "press figure min-h-9 rounded-pill border px-3 text-sm font-medium",
              parsed === value ? "border-tone-soft bg-tone-soft text-ink" : "border-rule text-ink-2 hover:bg-paper-3",
            )}
          >
            {value} {unitLabel(unit, t)}
          </button>
        ))}
      </div>
      {units.length > 0 && <Chips wrap label={t("food.unit")} options={units} value={unit} onChange={setUnit} />}

      <dl className="grid grid-cols-4 gap-2 border-t border-rule pt-4" aria-live="polite">
        {[
          { label: t("unit.kcal"), value: portion ? num(portion.kcal, 0) : "–", strong: true },
          { label: t("food.protein"), value: portion ? num(portion.protein) : "–" },
          { label: t("food.fat"), value: portion ? num(portion.fat) : "–" },
          { label: t("food.carbs"), value: portion ? num(portion.carbs) : "–" },
        ].map((item) => (
          <div key={item.label} className="min-w-0">
            <dd className={cn("figure", item.strong ? "text-xl text-ink" : "text-md font-medium text-ink-2")}>{item.value}</dd>
            <dt className="mt-0.5 truncate text-xs text-muted">{item.label}</dt>
          </div>
        ))}
      </dl>

      <div className="mt-auto space-y-2 pt-2">
        <Button variant="primary" size="lg" block disabled={!valid} busy={busy} onClick={() => valid && onAdd(clamp(parsed, 0.1, MAX_AMOUNT), unit)}>
          {t("food.addTo", { meal: mealName })}
        </Button>
        {product.is_own &&
          (confirming ? (
            <div className="flex gap-2">
              <Button block onClick={() => setConfirming(false)}>
                {t("common.cancel")}
              </Button>
              <Button variant="danger" block busy={remove.isPending} onClick={() => remove.mutate(product.id, { onSuccess: onDeleted })}>
                {t("product.deleteConfirm")}
              </Button>
            </div>
          ) : (
            <Button variant="quiet" block onClick={() => setConfirming(true)}>
              {t("product.delete")}
            </Button>
          ))}
      </div>
    </div>
  );
}

function DishView({ dish, mealName, busy, onAdd, onDeleted }: { dish: Dish; mealName: string; busy: boolean; onAdd: () => void; onDeleted: () => void }) {
  const { t } = useT();
  const remove = useDeleteDish();
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="flex h-full flex-col gap-4">
      <ul className="divide-y divide-rule">
        {dish.items.map((item) => (
          <li key={item.product_id} className="flex items-baseline justify-between gap-3 py-2.5">
            <span className="min-w-0">{item.name}</span>
            <span className="figure shrink-0 text-sm font-normal text-muted">
              {num(item.amount)} {unitLabel(item.unit, t)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-sm text-ink-2">{t("dish.total", { kcal: num(dish.totals.calories, 0), p: num(dish.totals.protein, 0), f: num(dish.totals.fat, 0), c: num(dish.totals.carbs, 0) })}</p>
      <div className="mt-auto space-y-2 pt-2">
        <Button variant="primary" size="lg" block busy={busy} onClick={onAdd}>
          {t("food.addTo", { meal: mealName })}
        </Button>
        {confirming ? (
          <div className="flex gap-2">
            <Button block onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="danger" block busy={remove.isPending} onClick={() => remove.mutate(dish.id, { onSuccess: onDeleted })}>
              {t("dish.deleteConfirm")}
            </Button>
          </div>
        ) : (
          <Button variant="quiet" block onClick={() => setConfirming(true)}>
            {t("dish.delete")}
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * Find a food and add it. The "+" on a row adds the usual portion in one
 * tap; the row itself opens the amount. The sheet stays open, so a whole
 * meal goes in without coming back.
 */
export function FoodPicker({
  initialCategory,
  date,
  startWithScan = false,
  onClose,
}: {
  initialCategory?: MealCategory;
  /** Another day than today, as YYYY-MM-DD. */
  date?: string;
  startWithScan?: boolean;
  onClose: () => void;
}) {
  const { t } = useT();
  const log = useLogFood();
  const [category, setCategory] = useState<MealCategory>(initialCategory ?? mealForNow());
  const [shelf, setShelf] = useState<Shelf>("recent");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<View>(startWithScan ? { name: "scan" } : { name: "list" });
  const [added, setAdded] = useState<{ count: number; kcal: number }>({ count: 0, kcal: 0 });
  const [fresh, setFresh] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const search = useDebounced(query.trim());
  const searching = search.length > 0;
  const products = useProducts(searching ? "search" : shelf === "dishes" ? "recent" : shelf, search, searching || shelf !== "dishes");
  const dishes = useDishes(!searching && shelf === "dishes");
  const mealName = t(`meal.${category}`);

  // The tick on a row that was just added fades back to a plus.
  useEffect(() => {
    if (!fresh) return;
    const timer = window.setTimeout(() => setFresh(null), 1400);
    return () => window.clearTimeout(timer);
  }, [fresh]);

  const toList = () => {
    setView({ name: "list" });
    setQuery("");
    window.setTimeout(() => input.current?.focus(), 0);
  };

  const record = (key: string, kcal: number) => {
    setAdded((current) => ({ count: current.count + 1, kcal: current.kcal + kcal }));
    setFresh(key);
  };

  const addProduct = (product: Product, amount: number, unit: FoodUnit, then?: () => void) =>
    log.mutate(
      { category, date, items: [{ productId: product.id, amount, unit }] },
      {
        onSuccess: () => {
          record(`p${product.id}`, portionOf(product, amount, unit).kcal);
          then?.();
        },
      },
    );

  const addDish = (dish: Dish, then?: () => void) =>
    log.mutate(
      { category, date, dishId: dish.id },
      {
        onSuccess: () => {
          record(`d${dish.id}`, dish.totals.calories);
          then?.();
        },
      },
    );

  const shelves: Option<Shelf>[] = [
    { id: "recent", label: t("food.shelf.recent") },
    { id: "favorites", label: t("food.shelf.favorites") },
    { id: "mine", label: t("food.shelf.mine") },
    { id: "dishes", label: t("food.shelf.dishes") },
  ];
  const meals: Option<MealCategory>[] = MEAL_CATEGORIES.map((id) => ({ id, label: t(`meal.${id}`) }));

  const quickButton = (key: string, label: string, onClick: () => void) => (
    <IconButton tonal label={label} disabled={log.isPending} onClick={onClick} className={cn("mr-2", fresh === key && "bg-tone-soft text-ink")}>
      {fresh === key ? <Check size={18} className="anim-tick" /> : <Plus size={18} />}
    </IconButton>
  );

  const createRow = (initialName?: string) => (
    <button
      type="button"
      onClick={() => setView({ name: "create", initialName })}
      className="press flex min-h-[3.25rem] w-full items-center gap-3 rounded-control px-3 text-left font-medium text-ink-2 hover:bg-paper-3 hover:text-ink"
    >
      <Plus size={18} aria-hidden="true" />
      {t("product.new")}
    </button>
  );

  const title =
    view.name === "portion" ? view.product.name : view.name === "dish" ? view.dish.name : view.name === "create" ? t("product.new") : view.name === "scan" ? t("scan.title") : t("food.title");

  const list = searching || shelf !== "dishes" ? (products.data ?? []) : [];

  return (
    <Sheet
      open
      size="tall"
      tone="nutrition"
      onClose={onClose}
      onBack={view.name === "list" ? undefined : toList}
      title={title}
      footer={
        view.name === "list" && added.count > 0 ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-ink-2" aria-live="polite">
              {t("food.added", { n: added.count, kcal: num(added.kcal, 0) })}
            </p>
            <Button variant="primary" onClick={onClose}>
              {t("common.done")}
            </Button>
          </div>
        ) : undefined
      }
    >
      {view.name === "portion" && (
        <PortionView
          key={view.product.id}
          product={view.product}
          mealName={mealName}
          busy={log.isPending}
          onAdd={(amount, unit) => addProduct(view.product, amount, unit, toList)}
          onDeleted={toList}
        />
      )}
      {view.name === "dish" && <DishView dish={view.dish} mealName={mealName} busy={log.isPending} onAdd={() => addDish(view.dish, toList)} onDeleted={toList} />}
      {view.name === "create" && (
        <ProductForm initialName={view.initialName} barcode={view.barcode} onCreated={(product) => setView({ name: "portion", product })} />
      )}
      {view.name === "scan" && (
        <BarcodeScanner onProduct={(product) => setView({ name: "portion", product })} onCreate={(barcode) => setView({ name: "create", barcode })} />
      )}

      {view.name === "list" && (
        <div data-tone="nutrition" className="space-y-3">
          <Chips label={t("food.meal")} options={meals} value={category} onChange={setCategory} />

          <div className="relative">
            <Search size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              ref={input}
              type="search"
              inputMode="search"
              enterKeyHint="search"
              autoFocus
              autoComplete="off"
              aria-label={t("food.search")}
              placeholder={t("food.search")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className={cn(controlClass, "pl-10 pr-[5.5rem]")}
            />
            <div className="absolute right-1 top-1/2 flex -translate-y-1/2">
              {query && (
                <IconButton
                  label={t("food.clear")}
                  onClick={() => {
                    setQuery("");
                    input.current?.focus();
                  }}
                >
                  <X size={18} />
                </IconButton>
              )}
              <IconButton label={t("scan.title")} onClick={() => setView({ name: "scan" })}>
                <ScanBarcode size={20} />
              </IconButton>
            </div>
          </div>

          {!searching && <Chips label={t("food.shelves")} options={shelves} value={shelf} onChange={setShelf} />}

          {!searching && shelf === "dishes" ? (
            dishes.isPending ? (
              <SkeletonRows rows={4} />
            ) : (dishes.data ?? []).length === 0 ? (
              <Empty title={t("dish.empty")} text={t("dish.emptyText")} />
            ) : (
              <ul className="-mx-4 divide-y divide-rule border-y border-rule">
                {(dishes.data ?? []).map((dish) => (
                  <li key={dish.id} className="flex items-center">
                    <button type="button" onClick={() => setView({ name: "dish", dish })} className="min-h-[3.25rem] min-w-0 flex-1 px-4 py-2 text-left hover:bg-paper-3">
                      <span className="block truncate font-medium">{dish.name}</span>
                      <span className="block text-sm text-muted">
                        {t("dish.summary", { n: dish.items.length, kcal: num(dish.totals.calories, 0) })}
                      </span>
                    </button>
                    {quickButton(`d${dish.id}`, t("food.quickAdd", { name: dish.name }), () => addDish(dish))}
                  </li>
                ))}
              </ul>
            )
          ) : products.isPending ? (
            <SkeletonRows rows={6} />
          ) : list.length === 0 ? (
            <>
              <Empty
                title={searching ? t("food.none", { query: search }) : t(`food.empty.${shelf === "dishes" ? "recent" : shelf}`)}
                text={searching ? t("food.noneText") : t(`food.emptyText.${shelf === "dishes" ? "recent" : shelf}`)}
              />
              {(searching || shelf === "mine") && createRow(searching ? search : undefined)}
            </>
          ) : (
            <>
              <ul className="-mx-4 divide-y divide-rule border-y border-rule">
                {list.map((product) => {
                  const unit = product.default_unit;
                  const amount = defaultAmount(unit);
                  return (
                    <li key={product.id} className="flex items-center">
                      <button
                        type="button"
                        onClick={() => setView({ name: "portion", product })}
                        className="min-h-[3.25rem] min-w-0 flex-1 px-4 py-2 text-left hover:bg-paper-3"
                      >
                        <span className="block truncate font-medium">{product.name}</span>
                        <span className="block truncate text-sm text-muted">
                          {product.brand ? `${product.brand}, ` : ""}
                          {num(product.kcal_per_100g, 0)} {t("unit.kcal")} {t("food.per100")}
                        </span>
                      </button>
                      {quickButton(`p${product.id}`, t("food.quickAddAmount", { name: product.name, amount: `${amount} ${unitLabel(unit, t)}` }), () =>
                        addProduct(product, amount, unit),
                      )}
                    </li>
                  );
                })}
              </ul>
              {(searching || shelf === "mine") && createRow(searching ? search : undefined)}
            </>
          )}
        </div>
      )}
    </Sheet>
  );
}
