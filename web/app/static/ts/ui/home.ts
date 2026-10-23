// Home tab: the week at a glance and eight small tiles that lead to entering or viewing data.

import {
    mount, render, api, loadAll, defineSheets, defineActions, openSheet, toast, head, doneFoot, tipCard, Tip,
    t, tn, form, I, esc, fmtN, U, LANG, TK, TODAY, key, addDays, mondayOf, dayLong, wd2,
    durHtml, dur, clock, litNum, liters, kg, signed, pbar, segs, mbars, spark, lastDays,
} from "./core.js";
import { defineDaySheet, openFromHash } from "./common.js";
import { showStreak, streakOf } from "./shell.js";

interface HeatDay {
    date: string;
    nutrition: { calories: number; protein: number; water: number };
    recovery: { sleep_hours: number };
    training: { completed: boolean; exercise_count: number };
}
interface WeekDay { key: string; date: string; exercises: number; rest: boolean; completed: boolean; is_today: boolean; }

const UID = document.body.dataset.uid || "";
const S: {
    day?: any; heat: Record<string, HeatDay>; week?: WeekDay[]; plan?: { id: number; name: string } | null;
    stats?: any; sleep?: any; stretched: boolean; loaded: boolean;
} = { heat: {}, stretched: false, loaded: false };

const H = (k: string): HeatDay | undefined => S.heat[k];
const last7 = <T>(fn: (d: HeatDay | undefined) => T): T[] => lastDays(7).map((k) => fn(H(k)));
const WATER_STEP = 0.25;
const waterGoal = (): number => S.day?.water_goal || 2.5;

function bedtime(): { at: number; debt: number } | null {
    const wake = S.sleep?.wake_time ? new Date(S.sleep.wake_time) : null;
    const debt = lastDays(7).reduce((s, k) => {
        const h = H(k)?.recovery.sleep_hours || 0;
        return s + (h ? Math.max(0, 480 - h * 60) : 0);
    }, 0);
    if (!wake) return null;
    const wakeMin = wake.getHours() * 60 + wake.getMinutes();
    return { at: wakeMin - 480 - (debt >= 60 ? 30 : 0) + 1440, debt: Math.round(debt) };
}

function tips(): Tip[] {
    const out: Tip[] = [];
    const d = S.day;
    const bed = bedtime();
    if (bed && bed.debt >= 30) out.push({ c: "var(--sleep)", icon: "moon", t: t("tips.bedT", { time: clock(bed.at) }), d: t("tips.bedD", { debt: dur(bed.debt) }), href: "/recovery/#sheet:sleep", cta: t("cta.sleep") });
    if (d && d.protein_goal && d.protein_goal - d.protein > 10) out.push({ c: "var(--protein)", icon: "egg", t: t("tips.protT", { g: fmtN(d.protein_goal - d.protein) }), d: t("tips.protD"), href: "/nutrition/#sheet:meal", cta: t("cta.meal") });
    const today = S.week?.find((w) => w.is_today);
    if (today && !today.rest && !today.completed) out.push({ c: "var(--train)", icon: "train", t: t("tips.planT"), d: tn("tips.planD", today.exercises), href: "/training/#sheet:workout", cta: t("cta.workout") });
    if (d && d.water_goal && d.water_goal - d.water > 0.2) out.push({ c: "var(--water)", icon: "drop", t: t("tips.waterT", { v: liters(d.water_goal - d.water) }), d: t("tips.waterD"), href: "/nutrition/#sheet:water", cta: t("cta.water") });
    if (!S.plan) out.push({ c: "var(--train)", icon: "list", t: t("tips.noPlanT"), d: t("tips.noPlanD"), href: "/training/#sheet:plan", cta: t("cta.plan") });
    return out;
}

interface TileSpec { k: string; c: string; icon: string; href?: string; open?: string; v: string; sub?: string; ind: string; hist?: string; add?: string; addL?: string; }
function tile(area: string, o: TileSpec): string {
    const target = o.href ? `data-href="${o.href}"` : `data-open="${o.open}"`;
    return `<div class="w tile ${o.hist ? "" : "grow"}" style="grid-area:${area};--c:${o.c}" role="button" tabindex="0" ${target} aria-label="${esc(t("tile." + o.k))}">
      <div class="t-top"><span class="ico">${I(o.icon)}</span><span class="t-l">${t("tile." + o.k)}</span>${o.add ? `<button type="button" class="t-add" data-act="${o.add}" aria-label="${esc(o.addL || "")}">${I("plus")}</button>` : ""}</div>
      <div class="t-v">${o.v}</div>
      ${o.sub ? `<div class="t-s">${o.sub}</div>` : ""}
      ${o.hist ? `<div class="t-h">${o.hist}</div>` : ""}
      <div class="t-i">${o.ind}</div>
    </div>`;
}

function page() {
    const d = S.day || {};
    const mon = mondayOf(TODAY);
    const week = Array.from({ length: 7 }, (_, i) => {
        const day = addDays(mon, i), k = key(day), fut = k > TK, h = H(k);
        const dots: [string, boolean][] = [
            ["var(--train)", !!h?.training.completed], ["var(--food)", (h?.nutrition.calories || 0) > 0], ["var(--sleep)", (h?.recovery.sleep_hours || 0) > 0],
        ];
        return `<button type="button" class="wk-d ${k === TK ? "on" : ""}" ${fut ? "disabled" : `data-open="day" data-arg="${k}"`} aria-label="${esc(dayLong(day))}"><span class="wk-n">${wd2(i)}</span><b>${day.getDate()}</b><span class="wk-dots">${dots.map(([c, on]) => `<i class="${on && !fut ? "on" : ""}" style="--c:${c}"></i>`).join("")}</span></button>`;
    }).join("");

    const today = S.week?.find((w) => w.is_today);
    let wv = "<b>—</b>", wsub = S.loaded ? t("home.noPlan") : "", wdone = 0, wall = 1;
    if (today) {
        if (today.rest) { wsub = t("wo.rest"); }
        else {
            wv = `<b>${fmtN(today.exercises)}</b><small>${form("u.ex", today.exercises)}</small>`;
            wsub = today.completed ? t("common.done") : t("home.byPlan");
            wall = Math.max(1, today.exercises); wdone = today.completed ? wall : 0;
        }
    }
    const sleepMin = Math.round((H(TK)?.recovery.sleep_hours || 0) * 60);
    const weights: number[] = S.stats?.weight?.values || [];
    const w = S.stats?.current_weight ?? (weights.length ? weights[weights.length - 1] : null);
    const wDelta = weights.length > 1 ? weights[weights.length - 1] - weights[0] : null;
    const wg = waterGoal(), cups = Math.round(wg / WATER_STEP);

    const tiles: TileSpec[] = [
        { k: "kcal", c: "var(--food)", icon: "food", href: "/nutrition/#sheet:meal", v: `<b>${fmtN(d.kcal || 0)}</b><small>${U("kcal")}</small>`, sub: d.kcal_goal ? t("home.of", { v: fmtN(d.kcal_goal) }) : "", ind: pbar(d.kcal_goal ? (d.kcal || 0) / d.kcal_goal : 0), hist: mbars(last7((h) => h?.nutrition.calories || null), 3200) },
        { k: "protein", c: "var(--protein)", icon: "egg", href: "/nutrition/#sheet:meal", v: `<b>${fmtN(d.protein || 0)}</b><small>${U("g")}</small>`, sub: d.protein_goal ? t("home.of", { v: `${fmtN(d.protein_goal)} ${U("g")}` }) : "", ind: pbar(d.protein_goal ? (d.protein || 0) / d.protein_goal : 0), hist: mbars(last7((h) => h?.nutrition.protein || null), 200) },
        { k: "water", c: "var(--water)", icon: "drop", href: "/nutrition/#sheet:water", add: "water", addL: t("water.add"), v: `<b>${litNum(d.water || 0)}</b><small>${U("l")}</small>`, sub: d.water_goal ? t("home.of", { v: liters(d.water_goal) }) : "", ind: segs(Math.round((d.water || 0) / WATER_STEP), Math.min(cups, 14)), hist: mbars(last7((h) => h?.nutrition.water || null), 3.5) },
        { k: "workout", c: "var(--train)", icon: "train", href: "/training/", v: wv, sub: wsub, ind: segs(wdone, Math.min(wall, 10)), hist: mbars(last7((h) => h?.training.exercise_count || null), 8) },
        { k: "sleep", c: "var(--sleep)", icon: "moon", href: "/recovery/#sheet:sleep", v: sleepMin ? durHtml(sleepMin) : "<b>—</b>", sub: t("home.goal", { v: dur(480) }), ind: mbars(last7((h) => h?.recovery.sleep_hours || null), 10) },
        { k: "stretch", c: "var(--mob)", icon: "stretch", href: "/recovery/#sheet:stretch", v: `<b>4</b><small>${U("min")}</small>`, sub: S.stretched ? t("common.done") : t("home.forLegs"), ind: segs(S.stretched ? 4 : 0, 4) },
        { k: "weight", c: "var(--good)", icon: "scale", href: "/nutrition/#sheet:weight", v: w != null ? `<b>${fmtN(w, 1)}</b><small>${U("kg")}</small>` : "<b>—</b>", sub: wDelta != null ? t("home.month", { v: signed(wDelta, kg) }) : "", ind: spark(weights) },
        { k: "steps", c: "var(--rec)", icon: "walk", open: "band", v: "<b>—</b>", sub: t("home.bandSoon"), ind: pbar(0) },
    ];
    return {
        cls: "pg-home",
        html: `<section class="w week auto" aria-label="${esc(t("home.week"))}">${week}</section>${tiles.map((o, i) => tile("t" + (i + 1), o)).join("")}${tipCard(tips())}`,
    };
}

defineDaySheet();
defineSheets({
    band: () => ({
        c: "var(--rec)",
        html: head(t("band.title"), "") + `<div class="sh-b">
          <div class="dev"><span class="ico" style="--c:var(--rec)">${I("band")}</span><span class="dev-b"><b>${t("band.soonT")}</b><span>${t("band.soonD")}</span></span></div>
          <ul class="dl">${["mi", "apple", "samsung"].map((s) => `<li><span class="ico" style="--c:var(--rec)">${I("band")}</span><span class="dl-b"><b>${t("band." + s)}</b><span>${t("band." + s + "Via")}</span></span></li>`).join("")}</ul>
        </div>` + doneFoot(),
    }),
});
defineActions({
    async water(el) {
        el.setAttribute("disabled", "");
        try {
            const r = await api<{ amount: number }>("/api/nutrition/water", { method: "POST", body: { amount: WATER_STEP } });
            S.day = { ...S.day, water: r.amount };
            toast(t("water.added", { v: liters(r.amount) }));
            render();
        } catch {
            toast(t("err.save"));
            el.removeAttribute("disabled");
        }
    },
});
document.addEventListener("click", (e) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>("[data-href]");
    if (el && !(e.target as HTMLElement).closest("[data-act]")) location.href = el.dataset.href || "/";
});

async function load(): Promise<void> {
    const r = await loadAll({
        day: api(`/api/nutrition/day?locale=${LANG}`),
        heat: api<{ days: HeatDay[] }>("/api/dashboard/heatmap"),
        plans: api<any[]>("/api/training/plans"),
        stats: api("/api/nutrition/stats?days=30"),
        sleep: api<any>(`/api/recovery/day-details/${UID}?date=${TK}`),
        habits: api<any[]>(`/api/recovery/habits/user/${UID}`),
    });
    S.day = r.day;
    for (const h of r.heat?.days || []) S.heat[h.date] = h;
    showStreak(streakOf(r.heat?.days || [], TK));
    S.stats = r.stats;
    S.sleep = r.sleep?.sleep;
    S.stretched = (r.habits || []).some((h: any) => h.slug === "stretching" && h.completed);
    S.plan = (r.plans || []).find((p: any) => p.is_active) || null;
    if (S.plan) {
        const wk = await api<{ days: WeekDay[] }>(`/api/training/plans/${S.plan.id}/week`).catch(() => null);
        S.week = wk?.days;
    }
    S.loaded = true;
    render();
    openFromHash(openSheet);
}

mount(page);
void load();
