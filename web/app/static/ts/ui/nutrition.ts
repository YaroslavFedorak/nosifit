// Nutrition tab: today's calories and macros, the four meals, water, the month heatmap and tips.
// A meal opens a sheet to add, change and remove foods; the full catalog (favourites, barcode,
// own products) is the existing picker, opened from the same sheet.

import {
    mount, render, refresh, api, loadAll, defineSheets, defineActions, openSheet, closeSheet, drawSheet, toast, head, doneFoot,
    saveFoot, tipCard, heatCard, Tip, t, tn, form, I, esc, fmtN, U, LANG, TK, TODAY,
    liters, litNum, kg, signed, pbar, spark, stepper, fitList, setSheetArg, sheetArg, monthKeys, monthsBack, avg, clamp,
} from "./core.js";
import { defineDaySheet, openFromHash } from "./common.js";

type Unit = "g" | "ml" | "pcs";
interface Entry { id: number; product_id: number; name: string; amount: number; unit: Unit; calories: number; protein: number; }
interface Meal { id: number; category: string; total_calories: number; total_protein: number; items: Entry[]; }
interface Product { id: number; name: string; brand: string | null; kcal_per_100g: number; protein_per_100g: number; default_unit: Unit; grams_per_unit: number | null; }
interface HeatDay { date: string; kcal: number; percent: number; calorie_goal: number; }

const MEALS = ["breakfast", "lunch", "snack", "dinner"];
const WATER_STEP = 0.25;
const S: {
    day?: any; heat: Record<string, HeatDay>; years: Set<number>; off: number; stats?: any; recs: any[];
    q: string; found: Product[] | null; recent: Product[]; busy: boolean; weight: number | null;
} = { heat: {}, years: new Set(), off: 0, recs: [], q: "", found: null, recent: [], busy: false, weight: null };

const mealsOf = (cat: string): Meal[] => (S.day?.meals || []).filter((m: Meal) => m.category === cat);
const entriesOf = (cat: string): Entry[] => mealsOf(cat).flatMap((m) => m.items);
const catKcal = (cat: string): number => mealsOf(cat).reduce((s, m) => s + m.total_calories, 0);
const nextMeal = (): string => {
    const h = new Date().getHours();
    const byTime = h < 11 ? "breakfast" : h < 16 ? "lunch" : h < 18 ? "snack" : "dinner";
    return entriesOf(byTime).length ? MEALS.find((m) => !entriesOf(m).length) || byTime : byTime;
};
const waterGoal = (): number => S.day?.water_goal || 2.5;
const unitLabel = (u: Unit): string => U(u === "pcs" ? "pcs" : u);
const amountText = (a: number, u: Unit): string => `${fmtN(a, a % 1 ? 1 : 0)} ${unitLabel(u)}`;
const defaultAmount = (p: Product): number => (p.default_unit === "pcs" ? 1 : p.default_unit === "ml" ? 250 : 100);
const grams = (p: Product, a: number): number => (p.default_unit === "g" ? a : a * (p.grams_per_unit || 1));
const step = (e: Entry): number => (e.unit === "pcs" ? 1 : e.unit === "ml" ? 50 : e.amount < 100 ? 10 : 25);

/* ---------- Level of a day: how close the calories came to the goal ---------- */
const level = (k: string): number => {
    const h = S.heat[k];
    if (!h || !h.kcal || k === TK || !h.calorie_goal) return 0;
    const r = Math.abs(h.percent - 100);
    return r <= 6 ? 4 : r <= 12 ? 3 : r <= 20 ? 2 : 1;
};

function tips(): Tip[] {
    const d = S.day, out: Tip[] = [];
    if (!d) return out;
    if (d.protein_goal && d.protein_goal - d.protein > 10)
        out.push({ c: "var(--protein)", icon: "egg", t: t("tips.protT", { g: fmtN(d.protein_goal - d.protein) }), d: t("tips.protD"), open: "meal", arg: "dinner", cta: t("cta.meal") });
    if (d.water_goal && d.water_goal - d.water > 0.2)
        out.push({ c: "var(--water)", icon: "drop", t: t("tips.waterT", { v: liters(d.water_goal - d.water) }), d: t("tips.waterD"), open: "water", cta: t("cta.water") });
    if (d.kcal_remaining && d.kcal_remaining > 200)
        out.push({ c: "var(--food)", icon: "food", t: t("tips.kcalT", { v: fmtN(d.kcal_remaining) }), d: t("tips.kcalD"), open: "meal", arg: nextMeal(), cta: t("cta.meal") });
    for (const r of S.recs) {
        const map: Record<string, string> = { fiber: "fiber", sugar: "sugar", salt: "salt", saturated_fat: "satFat", quality: "quality" };
        const k = map[r.type];
        if (k) out.push({ c: "var(--food)", icon: "bowl", t: t(`tips.food.${k}T`), d: t(`tips.food.${k}D`), open: "meal", arg: nextMeal(), cta: t("cta.meal") });
    }
    if (d.goals_available === false) out.push({ c: "var(--good)", icon: "target", t: t("tips.goalsT"), d: t("tips.goalsD"), href: "/profile/account", cta: t("cta.params") });
    return out;
}

function page() {
    const d = S.day || {};
    const goal = d.kcal_goal || 0, left = Math.round(goal - (d.kcal || 0));
    const mac = (k: string, v: number, g: number, c: string) =>
        `<div class="mac" style="--c:${c}"><span class="mac-l">${t("mac." + k)}</span><span class="mac-v">${fmtN(v || 0)}<span>${g ? ` / ${fmtN(g)} ${U("g")}` : ` ${U("g")}`}</span></span>${pbar(g ? (v || 0) / g : 0)}</div>`;
    const hero = `<section class="w hero fh" style="--c:var(--food)">
      <div class="fh-top"><div class="fh-k"><b>${fmtN(d.kcal || 0)}</b><span>${goal ? `/ ${fmtN(goal)} ` : ""}${U("kcal")}</span></div>
        ${goal ? `<div class="fh-left"><b>${fmtN(Math.abs(left))}</b><span>${left >= 0 ? t("food.left") : t("food.over")}</span></div>` : ""}</div>
      ${pbar(goal ? (d.kcal || 0) / goal : 0, "thick")}
      <div class="macros">${mac("p", d.protein, d.protein_goal, "var(--protein)")}${mac("f", d.fat, d.fat_goal, "var(--fat)")}${mac("c", d.carb, d.carb_goal, "var(--carbs)")}</div>
      <ul class="meals">${MEALS.map((m) => {
        const k = Math.round(catKcal(m)), has = entriesOf(m).length > 0;
        return `<li><button type="button" class="meal ${has ? "has" : ""}" data-open="meal" data-arg="${m}"><span class="meal-b"><span class="meal-n">${t("meal." + m)}</span><span class="meal-v ${has ? "on" : ""}">${has ? `${fmtN(k)} ${U("kcal")}` : t("food.add")}</span></span><span class="meal-p">${I(has ? "edit" : "plus")}</span></button></li>`;
      }).join("")}</ul>
    </section>`;
    const n = Math.round((d.water || 0) / WATER_STEP), gN = clamp(Math.round(waterGoal() / WATER_STEP), 4, 14);
    const side = `<section class="w side wat" style="--c:var(--water)">
      <div class="w-h"><b>${t("tile.water")}</b><span class="wv"><b>${litNum(d.water || 0)}</b>${d.water_goal ? ` / ${liters(d.water_goal)}` : ` ${U("l")}`}</span></div>
      <div class="cups" style="--cols:${gN}; grid-template-columns: repeat(${gN}, minmax(0, 1fr))">${Array.from({ length: gN }, (_, i) => `<button type="button" class="cup ${i < n ? "on" : ""} ${i === n ? "nx" : ""}" data-act="cup" data-i="${i}" aria-label="${esc(liters((i + 1) * WATER_STEP))}"></button>`).join("")}</div>
      <div class="wat-f"><button type="button" class="btn sm ghost" data-act="waterD" data-d="-1">${I("minus")}<span>${fmtN(250)} ${U("ml")}</span></button><button type="button" class="btn sm" data-act="waterD" data-d="1">${I("plus")}<span>${fmtN(250)} ${U("ml")}</span></button></div>
    </section>`;
    const mk = monthKeys(S.off);
    const logged = mk.filter((k) => k !== TK && (S.heat[k]?.kcal || 0) > 0);
    const inTarget = logged.filter((k) => level(k) >= 3).length;
    const first = Object.keys(S.heat).sort().find((k) => (S.heat[k].kcal || 0) > 0) || null;
    const heat = heatCard({
        off: S.off, minOff: monthsBack(first), color: "var(--food)", label: t("heat.food"), level, mod: "food",
        stats: [[fmtN(inTarget), form("st.inTarget", inTarget)], [logged.length ? fmtN(avg(logged.map((k) => S.heat[k].kcal))) : "—", t("st.avgKcal")]],
        legend: [t("heat.lg.food.0"), t("heat.lg.food.1")],
    });
    return { cls: "pg-mod", html: hero + side + heat + tipCard(tips()) };
}

/* ---------- Data ---------- */

async function loadDay(): Promise<void> {
    S.day = await api(`/api/nutrition/day?locale=${LANG}`);
}
async function loadYear(y: number): Promise<void> {
    if (S.years.has(y)) return;
    S.years.add(y);
    const r = await api<{ days: HeatDay[] }>(`/api/nutrition/heatmap?year=${y}`);
    for (const h of r.days) S.heat[h.date] = h;
}
async function search(q: string): Promise<void> {
    S.q = q;
    if (!q.trim()) { S.found = null; drawList(); return; }
    try {
        const r = await api<{ products: Product[] }>(`/api/nutrition/products?q=${encodeURIComponent(q)}&limit=20&locale=${LANG}`);
        if (S.q === q) { S.found = r.products; drawList(); }
    } catch {
        toast(t("err.load"));
    }
}
let searchTimer = 0;

/* ---------- Meal sheet ---------- */

function foodRows(cat: string): string {
    const added = entriesOf(cat);
    const inMeal = new Set(added.map((e) => e.product_id));
    const sug = (S.found ?? S.recent).filter((p) => !inMeal.has(p.id));
    const rowE = (e: Entry) =>
        `<li class="fi on"><span class="fi-b"><b>${esc(e.name)}</b><span>${amountText(e.amount, e.unit)} · ${fmtN(e.calories)} ${U("kcal")}</span></span>${stepper("fq", "", e.name, `data-e="${e.id}"`).replace("<output></output>", "")}</li>`;
    const rowP = (p: Product) => {
        const a = defaultAmount(p);
        return `<li class="fi"><span class="fi-b"><b>${esc(p.name)}${p.brand ? ` <small class="muted">${esc(p.brand)}</small>` : ""}</b><span>${amountText(a, p.default_unit)} · ${fmtN((p.kcal_per_100g * grams(p, a)) / 100)} ${U("kcal")}</span></span><button type="button" class="fi-add" data-act="fadd" data-p="${p.id}" aria-label="${esc(t("food.addX", { x: p.name }))}">${I("plus")}</button></li>`;
    };
    const html = added.map(rowE).join("") + sug.map(rowP).join("");
    return html || `<li class="fl-empty">${S.found ? t("food.none") : t("food.searchHint")}</li>`;
}
function drawList(): void {
    const ul = document.getElementById("fl");
    if (!ul) return;
    ul.innerHTML = foodRows(sheetArg() || nextMeal());
    fitList(ul, document.getElementById("fl-more"), (n) => tn("food.more", n));
}

defineDaySheet();
defineSheets({
    meal(arg) {
        const m = MEALS.includes(arg || "") ? (arg as string) : nextMeal();
        const kc = catKcal(m), pr = mealsOf(m).reduce((s, x) => s + x.total_protein, 0);
        return {
            c: "var(--food)", tall: true,
            html: head(t("meal." + m), `${fmtN(kc)} ${U("kcal")} · ${t("mac.p")} ${fmtN(pr)} ${U("g")}`) + `<div class="sh-b">
              <div class="meal-sh"><div class="meal-l">
                <div class="tabs" role="tablist">${MEALS.map((x) => `<button type="button" role="tab" aria-selected="${x === m}" data-act="mealTab" data-v="${x}">${t("meal." + x)}</button>`).join("")}</div>
                <label class="search" for="fq">${I("search")}<input id="fq" type="search" autocomplete="off" placeholder="${esc(t("food.search"))}" value="${esc(S.q)}"></label>
                <button type="button" class="btn sm ghost" data-act="catalog">${I("scan")}<span>${t("food.catalog")}</span></button>
              </div><div class="meal-r">
                <ul class="fl" id="fl">${foodRows(m)}</ul>
                <p class="fl-more" id="fl-more" hidden></p>
              </div></div></div>` + doneFoot(),
            after: () => fitList(document.getElementById("fl"), document.getElementById("fl-more"), (n) => tn("food.more", n)),
        };
    },
    water() {
        const d = S.day || {};
        const n = Math.round((d.water || 0) / WATER_STEP), gN = clamp(Math.round(waterGoal() / WATER_STEP), 4, 14);
        return {
            c: "var(--water)",
            html: head(t("tile.water"), d.water_goal ? t("home.of", { v: liters(d.water_goal) }) : t("water.noGoal")) + `<div class="sh-b">
              <div class="big-stp"><button type="button" data-act="waterD" data-d="-1" aria-label="${esc(t("aria.less"))}">${I("minus")}</button><output>${litNum(d.water || 0)}<small>${U("l")}</small></output><button type="button" data-act="waterD" data-d="1" aria-label="${esc(t("water.add"))}">${I("plus")}</button></div>
              <div class="cups sh-cups" style="--cols:${gN}; grid-template-columns: repeat(${gN}, minmax(0, 1fr))">${Array.from({ length: gN }, (_, i) => `<button type="button" class="cup ${i < n ? "on" : ""} ${i === n ? "nx" : ""}" data-act="cup" data-i="${i}" aria-label="${esc(liters((i + 1) * WATER_STEP))}"></button>`).join("")}</div>
              <div class="wat-f">${[0.33, 0.5, 1].map((v) => `<button type="button" class="btn sm ghost" data-act="waterAdd" data-v="${v}">+ ${liters(v)}</button>`).join("")}</div>
            </div>` + doneFoot(),
        };
    },
    weight() {
        const vals: number[] = S.stats?.weight?.values || [];
        const cur = S.weight ?? S.stats?.current_weight ?? (vals.length ? vals[vals.length - 1] : 75);
        if (S.weight == null) S.weight = cur;
        const first = vals.length ? vals[0] : null;
        const labels: string[] = S.stats?.weight?.labels || [];
        return {
            c: "var(--good)", wide: true,
            html: head(t("tile.weight"), t("wt.today")) + `<div class="sh-b"><div class="wo-grid"><div class="wo-col">
              <div class="big-stp"><button type="button" data-act="wtD" data-d="-1" aria-label="${esc(t("aria.less"))}">${I("minus")}</button><output>${fmtN(S.weight || 0, 1)}<small>${U("kg")}</small></output><button type="button" data-act="wtD" data-d="1" aria-label="${esc(t("aria.more"))}">${I("plus")}</button></div>
              <div class="kv" style="--n:2"><div><b>${first != null ? signed((S.weight || 0) - first, kg) : "—"}</b><span>${t("wt.month")}</span></div><div><b>${vals.length ? fmtN(vals.length) : "—"}</b><span>${form("wt.weighings", vals.length)}</span></div></div>
            </div><div class="wo-col"><p class="ch-t">${t("wt.chart")}</p><div class="chart wt-ch" style="--c:var(--good)">${spark(vals) || `<span class="fl-empty">${t("common.noData")}</span>`}<div class="ch-x"><span>${esc(labels[0] || "")}</span><span class="on">${esc(labels[labels.length - 1] || "")}</span></div></div></div></div></div>` + saveFoot("wtSave"),
        };
    },
});

async function setWater(target: number): Promise<void> {
    const cur = S.day?.water || 0;
    const delta = Math.round((Math.max(0, target) - cur) * 1000) / 1000;
    if (!delta || S.busy) return;
    S.busy = true;
    try {
        const r = await api<{ amount: number }>("/api/nutrition/water", { method: "POST", body: { amount: clamp(delta, -5, 5) } });
        S.day = { ...S.day, water: r.amount };
        refresh();
    } catch {
        toast(t("err.save"));
    } finally {
        S.busy = false;
    }
}
async function reloadDay(): Promise<void> {
    try {
        await loadDay();
    } catch {
        toast(t("err.load"));
    }
    refresh();
}
let pickerReady: Promise<(mealId: number, meal?: any) => void> | null = null;
function picker(): Promise<(mealId: number, meal?: any) => void> {
    if (!pickerReady) {
        pickerReady = (async () => {
            const i18n = await import("../i18n/index.js");
            await i18n.loadTranslations("nutrition");
            const items = await import("../nutrition/modals/items.js");
            items.setupItemModals(async () => { await reloadDay(); });
            return items.openAddItemModal;
        })();
    }
    return pickerReady;
}

defineActions({
    mon(el) { S.off += Number(el.dataset.d); void ensureMonth().then(render); render(); },
    cup(el) { const i = Number(el.dataset.i), v = (i + 1) * WATER_STEP; void setWater(Math.abs((S.day?.water || 0) - v) < 0.01 ? i * WATER_STEP : v); },
    waterD(el) { void setWater((S.day?.water || 0) + WATER_STEP * Number(el.dataset.d)); },
    waterAdd(el) { void setWater((S.day?.water || 0) + Number(el.dataset.v)); },
    mealTab(el) { setSheetArg(el.dataset.v || "breakfast"); drawSheet(); },
    async fadd(el) {
        const p = (S.found ?? S.recent).find((x) => x.id === Number(el.dataset.p));
        if (!p || S.busy) return;
        S.busy = true;
        try {
            const r = await api<{ day?: any }>("/api/nutrition/log", {
                method: "POST",
                body: { category: sheetArg() || nextMeal(), items: [{ product_id: p.id, amount: defaultAmount(p), unit: p.default_unit }], locale: LANG, return: "day" },
            });
            if (r.day) S.day = r.day; else await loadDay();
            S.q = ""; S.found = null;
            refresh();
        } catch {
            toast(t("err.save"));
        } finally {
            S.busy = false;
        }
    },
    async fq(el) {
        const e = entriesOf(sheetArg() || nextMeal()).find((x) => x.id === Number(el.dataset.e));
        if (!e || S.busy) return;
        const amount = Math.round((e.amount + step(e) * Number(el.dataset.d)) * 10) / 10;
        S.busy = true;
        try {
            if (amount <= 0) await api(`/api/nutrition/entries/${e.id}`, { method: "DELETE" });
            else await api(`/api/nutrition/entries/${e.id}`, { method: "PATCH", body: { amount, unit: e.unit, locale: LANG } });
            await loadDay();
            refresh();
        } catch {
            toast(t("err.save"));
        } finally {
            S.busy = false;
        }
    },
    async catalog() {
        const cat = sheetArg() || nextMeal();
        try {
            const open = await picker();
            let meal = mealsOf(cat)[0];
            if (!meal) meal = await api<Meal>("/api/nutrition/meals", { method: "POST", body: { category: cat, locale: LANG } });
            closeSheet();
            open(meal.id, meal);
        } catch {
            toast(t("err.load"));
        }
    },
    wtD(el) { S.weight = Math.round(((S.weight || 0) + 0.1 * Number(el.dataset.d)) * 10) / 10; drawSheet(); },
    async wtSave() {
        try {
            await api("/api/nutrition/weight", { method: "POST", body: { weight: S.weight } });
            S.stats = await api("/api/nutrition/stats?days=30").catch(() => S.stats);
            closeSheet();
            toast(t("common.saved"));
            render();
        } catch {
            toast(t("err.save"));
        }
    },
});
document.addEventListener("input", (e) => {
    const el = e.target as HTMLInputElement;
    if (el.id !== "fq") return;
    S.q = el.value;
    clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => void search(el.value), 220);
});

async function ensureMonth(): Promise<void> {
    const y = new Date(TODAY.getFullYear(), TODAY.getMonth() + S.off, 1).getFullYear();
    try { await loadYear(y); } catch { toast(t("err.load")); }
}

async function load(): Promise<void> {
    const r = await loadAll({
        day: api(`/api/nutrition/day?locale=${LANG}`),
        year: loadYear(TODAY.getFullYear()),
        prev: TODAY.getMonth() < 3 ? loadYear(TODAY.getFullYear() - 1) : Promise.resolve(),
        stats: api("/api/nutrition/stats?days=30"),
        recs: api<{ recommendations: any[] }>("/api/nutrition/recommendations"),
        recent: api<{ products: Product[] }>(`/api/nutrition/products/recent?locale=${LANG}`),
    });
    S.day = r.day;
    S.stats = r.stats;
    S.recs = r.recs?.recommendations || [];
    S.recent = r.recent?.products || [];
    render();
    openFromHash(openSheet);
}

mount(page);
void load();
