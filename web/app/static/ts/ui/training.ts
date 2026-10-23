// Training tab: today's planned workout with the muscles it works, a set-by-set logger,
// the week of the plan, the month heatmap and tips from the training model.

import {
    mount, render, refresh, api, loadAll, defineSheets, defineActions, openSheet, drawSheet, toast, head, doneFoot,
    tipCard, heatCard, Tip, t, tn, form, extra, I, esc, fmtN, U, LANG, TK, TODAY, mondayOf, addDays, key, wdName, dayShort,
    figure, crop, MUSCLE_PARTS, stepper, monthKeys, monthsBack, sum, fitList,
} from "./core.js";
import { defineDaySheet, openFromHash } from "./common.js";

interface PlanEx { exercise: { id: string; slug: string; name: string; measurement_type?: string }; sets: number | null; reps: string | null; load: number | null; duration_sec: number | null; measurement_type?: string; }
interface WeekDay { key: string; date: string; exercises: number; rest: boolean; completed: boolean; session_id: number | null; is_today: boolean; }
interface SetEntry { reps?: number; duration_sec?: number; load: number; }
interface WorkEx { id: string; slug: string; name: string; sets: number; reps: number; load: number; timed: boolean; }
interface HeatDay { date: string; hard_sets: number; }

const MUSCLE_OF: Record<string, string | null> = (() => {
    try { return JSON.parse(document.getElementById("ux-ex-muscles")?.textContent || "{}"); } catch { return {}; }
})();

const S: {
    plan: { id: number; name: string } | null; week: WeekDay[]; today: PlanEx[]; muscles: Record<string, number>;
    heat: Record<string, HeatDay>; years: Set<number>; off: number; recs?: any; loaded: boolean;
    wo: { list: WorkEx[]; ex: number; log: SetEntry[][]; w: number; r: number; status: "idle" | "active" | "done"; saved?: number };
    q: string; found: any[] | null; recent: any[]; busy: boolean;
} = {
    plan: null, week: [], today: [], muscles: {}, heat: {}, years: new Set(), off: 0, loaded: false,
    wo: { list: [], ex: 0, log: [], w: 0, r: 0, status: "idle" }, q: "", found: null, recent: [], busy: false,
};

const exName = (slug: string, fallback: string): string => extra(`exercises.${slug}.name`, fallback);
const todayDay = (): WeekDay | undefined => S.week.find((d) => d.is_today);
const planned = (): boolean => !!S.plan && !!todayDay() && !todayDay()!.rest && S.today.length > 0;
const doneToday = (): boolean => !!todayDay()?.completed || S.wo.status === "done";
const muscleOf = (slug: string): string => MUSCLE_OF[slug] || "chest";
const level = (k: string): number => {
    const v = S.heat[k]?.hard_sets || 0;
    return !v ? 0 : v < 6 ? 1 : v < 11 ? 2 : v < 16 ? 3 : 4;
};

function tips(): Tip[] {
    const out: Tip[] = [];
    if (planned() && !doneToday()) out.push({ c: "var(--train)", icon: "train", t: t("tips.planT"), d: tn("tips.planD", S.today.length), open: "workout", cta: t("cta.workout") });
    const g = S.recs?.guidance;
    for (const m of (g?.muscles || []).slice(0, 2)) {
        const sets = m.params?.sets || 2;
        out.push({ c: "var(--train)", icon: "target", t: t("tips.addT", { m: t("mus." + m.muscle) }), d: tn("tips.addD", sets), open: "workout", cta: t("cta.workout") });
    }
    for (const w of (g?.warnings || []).filter((x: any) => x.kind === "rest").slice(0, 1))
        out.push({ c: "var(--r-mod)", icon: "body", t: t("tips.restT", { m: t("mus." + w.muscle) }), d: t("tips.restD"), href: "/recovery/#sheet:muscle:" + w.muscle, cta: t("cta.muscle") });
    if (!S.plan && S.loaded) out.push({ c: "var(--train)", icon: "list", t: t("tips.noPlanT"), d: t("tips.noPlanD"), act: "plan", cta: t("cta.plan") });
    return out;
}

function hero(): string {
    const d = todayDay();
    const sets = sum(S.today.map((e) => e.sets || 0));
    let title = t("wo.noPlan"), meta = t("wo.noPlanD"), btn = "";
    const color = (part: string): string | null => {
        const hit = Object.keys(S.muscles).some((m) => (S.muscles[m] || 0) > 0 && (MUSCLE_PARTS[m] || [m]).includes(part));
        return hit ? "var(--train)" : null;
    };
    if (S.plan && d) {
        if (d.rest) {
            const next = S.week.find((w) => w.date > TK && !w.rest);
            title = t("wo.restDay");
            meta = next ? t("wo.nextOn", { d: wdName(new Date(next.date + "T12:00:00")) }) : S.plan.name;
        } else {
            title = esc(S.plan.name);
            meta = `${tn("pl.ex", S.today.length)}${sets ? ` · ${tn("pl.sets", sets)}` : ""}`;
        }
    }
    if (planned()) btn = doneToday()
        ? `<button type="button" class="btn big ghost" data-open="workout">${I("check")}<span>${t("wo.review")}</span></button>`
        : `<button type="button" class="btn big" data-open="workout">${I("play")}<span>${S.wo.status === "active" ? t("wo.continue") : t("wo.start")}</span></button>`;
    else btn = `<div class="wo-nav"><button type="button" class="btn big ghost" data-act="plan">${I("list")}<span>${S.plan ? t("wo.editPlan") : t("cta.plan")}</span></button><button type="button" class="btn big" data-act="free">${I("plus")}<span>${t("wo.free")}</span></button></div>`;
    return `<section class="w hero tr" style="--c:var(--train)">
      <div class="h-top"><span class="eyebrow">${t("common.today")} · ${wdName(TODAY)}</span>${doneToday() ? `<span class="badge">${I("check")}${t("common.done")}</span>` : ""}</div>
      <h2 class="h-title">${title}</h2>
      <div class="h-meta">${meta}</div>
      <div class="tr-b"><div class="figfit" aria-hidden="true">${figure("ante", { color })}${figure("post", { color })}</div></div>
      ${btn}
    </section>`;
}

function weekCard(): string {
    const mon = mondayOf(TODAY);
    const days = S.plan && S.week.length ? S.week : Array.from({ length: 7 }, (_, i) => ({ key: "", date: key(addDays(mon, i)), exercises: 0, rest: true, completed: false, session_id: null, is_today: key(addDays(mon, i)) === TK }));
    const plannedN = days.filter((d) => !d.rest).length, doneN = days.filter((d) => d.completed).length;
    const items = days.map((d, i) => {
        let st = "rest", icon = "rest", s = "";
        if (!d.rest) {
            if (d.completed) { st = "done"; icon = "check"; s = t("common.done"); }
            else if (d.date === TK) { st = "today"; icon = "train"; s = t("common.today"); }
            else if (d.date < TK) { st = "miss"; icon = "close"; s = t("wo.missed"); }
            else { st = "plan"; icon = "train"; s = dayShort(new Date(d.date + "T12:00:00")); }
        }
        const name = d.rest ? t("wo.rest") : tn("pl.ex", d.exercises);
        return `<li class="wkp-d ${st} ${d.date === TK ? "today" : ""}"><span class="wkp-wd">${t("wd2." + i)}</span><span class="wkp-ic">${I(icon)}</span><span class="wkp-n"><span class="nf">${name}</span>${d.rest ? "" : `<span class="ns">${fmtN(d.exercises)}</span>`}</span><span class="wkp-s">${s}</span></li>`;
    }).join("");
    return `<section class="w side wkp" style="--c:var(--train)">
      <div class="w-h"><b>${t("wo.week")}</b><button type="button" class="wkp-edit" data-act="plan" title="${esc(t("wo.editPlan"))}">${S.plan ? t("wo.weekDone", { a: fmtN(doneN), b: fmtN(plannedN) }) : t("wo.noPlanShort")}${I("edit")}</button></div>
      <ol class="wkp-l">${items}</ol>
    </section>`;
}

function page() {
    const mk = monthKeys(S.off);
    const days = mk.filter((k) => (S.heat[k]?.hard_sets || 0) > 0);
    const hard = Math.round(sum(days.map((k) => S.heat[k].hard_sets)));
    const first = Object.keys(S.heat).sort().find((k) => (S.heat[k].hard_sets || 0) > 0) || null;
    const heat = heatCard({
        off: S.off, minOff: monthsBack(first), color: "var(--train)", label: t("heat.train"), level, mod: "train",
        stats: [[fmtN(days.length), form("st.workouts", days.length)], [fmtN(hard), form("st.sets", hard)]],
        legend: [t("heat.lg.train.0"), t("heat.lg.train.1")],
    });
    return { cls: "pg-mod", html: hero() + weekCard() + heat + tipCard(tips()) };
}

/* ---------- Workout logger ---------- */

function startWith(list: WorkEx[]): void {
    S.wo = { list, ex: 0, log: list.map(() => []), w: list[0]?.load || 0, r: list[0]?.reps || 10, status: "active" };
}
function fromPlan(): WorkEx[] {
    return S.today.map((e) => {
        const timed = (e.measurement_type || e.exercise.measurement_type) === "duration";
        return {
            id: e.exercise.id, slug: e.exercise.slug, name: exName(e.exercise.slug, e.exercise.name),
            sets: e.sets || 3, reps: timed ? e.duration_sec || 30 : parseInt(e.reps || "10", 10) || 10, load: e.load || 0, timed,
        };
    });
}
const setText = (s: SetEntry): string => (s.duration_sec ? `${fmtN(s.duration_sec)} ${U("s")}` : `${s.load ? fmtN(s.load, s.load % 1 ? 1 : 0) + "×" : ""}${s.reps}`);

function workoutSheet() {
    const W = S.wo;
    if (W.status === "done" || (doneToday() && W.status === "idle")) {
        const list = W.list.length ? W.list : fromPlan();
        const logged = W.list.length ? W.log : list.map(() => []);
        const total = sum(logged.map((l) => l.length));
        return {
            c: "var(--train)",
            html: head(S.plan?.name ? esc(S.plan.name) : t("wo.free"), dayShort(TODAY)) + `<div class="sh-b"><div class="wo-done"><span class="ok">${I("check")}</span><h4>${t("wo.saved")}</h4>${total ? `<p class="muted">${tn("pl.sets", total)}</p>` : ""}</div>
              <div class="wo-list">${list.map((e, i) => `<div><span class="crop">${crop(muscleOf(e.slug), "var(--train)")}</span><span>${esc(e.name)}<small>${logged[i]?.length ? logged[i].map(setText).join(" · ") : tn("pl.sets", e.sets)}</small></span></div>`).join("")}</div>
            </div>` + doneFoot(),
        };
    }
    if (!W.list.length) return pickSheet();
    const e = W.list[W.ex], log = W.log[W.ex], full = log.length >= e.sets, last = W.ex === W.list.length - 1;
    const wOut = `${fmtN(W.w, W.w % 1 ? 1 : 0)}<small>${U("kg")}</small>`;
    const rOut = e.timed ? `${fmtN(W.r)}<small>${U("s")}</small>` : fmtN(W.r);
    const sets = Array.from({ length: Math.max(e.sets, log.length) }, (_, i) =>
        log[i] ? `<span class="done">${setText(log[i])}</span>` : `<span class="${i === log.length ? "on" : ""}">${t("wo.setN", { n: i + 1 })}</span>`).join("");
    return {
        c: "var(--train)", wide: true,
        html: head(S.plan && planned() ? esc(S.plan.name) : t("wo.free"), t("wo.exOf", { a: W.ex + 1, b: W.list.length })) + `<div class="sh-b">
          <div class="wo-prog">${W.list.map((x, i) => `<i class="${i === W.ex ? "on" : W.log[i].length >= x.sets ? "done" : ""}"></i>`).join("")}</div>
          <div class="wo-grid"><div class="wo-col">
            <div class="wo-ex"><span class="crop">${crop(muscleOf(e.slug), "var(--train)")}</span><div class="wo-ex-b"><h4>${esc(e.name)}</h4><span>${t("mus." + muscleOf(e.slug))} · ${fmtN(e.sets)} × ${e.timed ? `${fmtN(e.reps)} ${U("s")}` : fmtN(e.reps)}</span></div></div>
            <div class="wo-sets">${sets}</div>
          </div><div class="wo-col">
            <div class="wo-st"><div class="stp-row"><span class="stp-l"><span>${t("wo.weight")}</span></span>${stepper("woW", wOut, t("wo.weight"))}</div><div class="stp-row"><span class="stp-l"><span>${e.timed ? t("wo.seconds") : t("wo.reps")}</span></span>${stepper("woR", rOut, t("wo.reps"))}</div></div>
            <div class="wo-nav"><button type="button" class="ib" data-act="woEx" data-d="-1" aria-label="${esc(t("common.back"))}" ${W.ex === 0 ? "disabled" : ""}>${I("prev")}</button>
              ${full ? `<button type="button" class="btn" data-act="${last ? "woFinish" : "woEx"}" data-d="1">${last ? t("wo.finish") : t("wo.nextEx")}</button>` : `<button type="button" class="btn" data-act="woSet">${I("check")}<span>${t("wo.logSet", { n: log.length + 1 })}</span></button>`}
              <button type="button" class="ib" data-act="${last ? "woFinish" : "woEx"}" data-d="1" aria-label="${esc(last ? t("wo.finish") : t("common.next"))}">${I(last ? "check" : "next")}</button></div>
          </div></div>
        </div>`,
    };
}

function pickRows(): string {
    const chosen = new Set(S.wo.list.map((e) => e.id));
    const items = (S.found ?? S.recent).filter((x) => !chosen.has(x.id));
    return items.map((x) => `<li class="fi"><span class="crop" style="width:40px;border-radius:10px">${crop(muscleOf(x.slug), "var(--train)")}</span><span class="fi-b"><b>${esc(exName(x.slug, x.name))}</b><span>${t("mus." + muscleOf(x.slug))}</span></span><button type="button" class="fi-add" style="background:var(--train)" data-act="pickEx" data-x="${esc(x.id)}" aria-label="${esc(t("common.add"))}">${I("plus")}</button></li>`).join("")
        || `<li class="fl-empty">${S.found ? t("wo.none") : t("wo.searchHint")}</li>`;
}
function pickSheet() {
    return {
        c: "var(--train)", tall: true,
        html: head(t("wo.free"), t("wo.pickHint")) + `<div class="sh-b">
          <label class="search" for="xq">${I("search")}<input id="xq" type="search" autocomplete="off" placeholder="${esc(t("wo.search"))}" value="${esc(S.q)}"></label>
          <ul class="fl" id="xl">${pickRows()}</ul><p class="fl-more" id="xl-more" hidden></p>
        </div>` + doneFoot(),
        after: () => fitList(document.getElementById("xl"), document.getElementById("xl-more"), (n) => tn("wo.more", n)),
    };
}

async function finish(): Promise<void> {
    const W = S.wo;
    const exercises = W.list.map((e, i) => ({ e, log: W.log[i] })).filter((x) => x.log.length).map(({ e, log }) => ({
        exercise: { id: e.id },
        sets: log.length,
        ...(e.timed ? { duration_sec: log[log.length - 1].duration_sec } : { reps: String(log[log.length - 1].reps) }),
        load: Math.max(...log.map((s) => s.load)),
        set_entries: log,
    }));
    if (!exercises.length) { toast(t("wo.nothing")); return; }
    S.busy = true;
    try {
        let sessionId: number | undefined;
        const d = todayDay();
        if (S.plan && d && !d.rest && !d.completed && planned()) {
            const c = await api<{ session_id: number }>(`/api/training/plans/${S.plan.id}/days/${d.key}/complete`, { method: "POST", body: {} });
            sessionId = c.session_id;
        }
        const saved = await api<{ id: number }>("/api/training/sessions/complete", { method: "POST", body: { session_id: sessionId, exercises } });
        W.status = "done";
        W.saved = saved.id;
        toast(t("wo.saved"));
        await loadWeek();
        void loadYear(TODAY.getFullYear(), true).then(render);
        refresh();
    } catch {
        toast(t("err.save"));
    } finally {
        S.busy = false;
    }
}

defineDaySheet();
defineSheets({
    workout() {
        if (S.wo.status === "idle" && planned() && !doneToday()) startWith(fromPlan());
        return workoutSheet();
    },
});

let searchTimer = 0;
async function searchEx(q: string): Promise<void> {
    S.q = q;
    if (!q.trim()) { S.found = null; drawSheet(); return; }
    try {
        const r = await api<{ items: any[] }>(`/api/training/exercises/search?q=${encodeURIComponent(q)}&locale=${LANG}`);
        if (S.q === q) { S.found = r.items; drawSheet(); }
    } catch {
        toast(t("err.load"));
    }
}
document.addEventListener("input", (e) => {
    const el = e.target as HTMLInputElement;
    if (el.id !== "xq") return;
    S.q = el.value;
    clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => void searchEx(el.value), 220);
});

defineActions({
    mon(el) { S.off += Number(el.dataset.d); void ensureMonth().then(render); render(); },
    free() {
        if (S.wo.status !== "active" || planned()) S.wo = { list: [], ex: 0, log: [], w: 0, r: 10, status: "active" };
        openSheet("workout");
    },
    pickEx(el) {
        const x = (S.found ?? S.recent).find((i) => String(i.id) === el.dataset.x);
        if (!x) return;
        const last = x.last || {};
        const timed = x.measurement_type === "duration";
        S.wo.list.push({ id: x.id, slug: x.slug, name: exName(x.slug, x.name), sets: last.sets || 3, reps: timed ? last.duration_sec || 30 : last.reps_count || 10, load: last.load || 0, timed });
        S.wo.log.push([]);
        S.wo.ex = S.wo.list.length - 1;
        S.wo.w = last.load || 0;
        S.wo.r = timed ? last.duration_sec || 30 : last.reps_count || 10;
        S.q = ""; S.found = null;
        drawSheet();
    },
    woW(el) { S.wo.w = Math.max(0, Math.round((S.wo.w + 2.5 * Number(el.dataset.d)) * 10) / 10); drawSheet(); },
    woR(el) {
        const e = S.wo.list[S.wo.ex];
        S.wo.r = Math.max(1, S.wo.r + (e?.timed ? 5 : 1) * Number(el.dataset.d));
        drawSheet();
    },
    woSet() {
        const W = S.wo, e = W.list[W.ex];
        W.log[W.ex].push(e.timed ? { duration_sec: W.r, load: W.w } : { reps: W.r, load: W.w });
        if (W.log[W.ex].length >= e.sets && W.ex < W.list.length - 1) {
            W.ex++;
            W.w = W.list[W.ex].load;
            W.r = W.list[W.ex].reps;
        }
        refresh();
    },
    woEx(el) {
        const W = S.wo;
        W.ex = Math.max(0, Math.min(W.list.length - 1, W.ex + Number(el.dataset.d)));
        W.w = W.list[W.ex].load;
        W.r = W.list[W.ex].reps;
        drawSheet();
    },
    woFinish() { if (!S.busy) void finish(); },
    plan() { void openPlanEditor(); },
});

/* ---------- Plan editor (the existing weekly plan modal) ---------- */

let editorReady: Promise<void> | null = null;
async function openPlanEditor(): Promise<void> {
    try {
        if (!editorReady) {
            editorReady = (async () => {
                const i18n = await import("../i18n/index.js");
                await i18n.loadTranslations("training");
                await i18n.loadTranslations("exercises").catch(() => undefined);
                const plans = await import("../training/plans.js");
                await plans.loadPlan();
                const picker = await import("../training/exercise_picker.js");
                picker.initExercisePicker();
                const editor = await import("../training/plan_modal.js");
                editor.initPlanModal();
                const modal = document.getElementById("tr-plan-modal");
                if (modal) {
                    // Saving or closing the editor changes the week, today's workout and the tips.
                    new MutationObserver(() => { if (!modal.classList.contains("open")) void reload(); })
                        .observe(modal, { attributes: true, attributeFilter: ["class"] });
                }
            })();
        }
        await editorReady;
        document.getElementById("tr-edit-plan")?.click();
    } catch {
        editorReady = null;
        toast(t("err.load"));
    }
}

/* ---------- Data ---------- */

async function loadYear(y: number, force = false): Promise<void> {
    if (S.years.has(y) && !force) return;
    S.years.add(y);
    const r = await api<{ days: HeatDay[] }>(`/api/training/heatmap?year=${y}`);
    for (const h of r.days) S.heat[h.date] = h;
}
async function ensureMonth(): Promise<void> {
    const y = new Date(TODAY.getFullYear(), TODAY.getMonth() + S.off, 1).getFullYear();
    try { await loadYear(y); } catch { toast(t("err.load")); }
}
async function loadWeek(): Promise<void> {
    if (!S.plan) return;
    const w = await api<{ days: WeekDay[] }>(`/api/training/plans/${S.plan.id}/week`).catch(() => null);
    S.week = w?.days || [];
}

async function reload(): Promise<void> {
    S.wo = { list: [], ex: 0, log: [], w: 0, r: 0, status: "idle" };
    await load(false);
}

async function load(first = true): Promise<void> {
    const r = await loadAll({
        plans: api<any[]>("/api/training/plans"),
        today: api<{ exercises: PlanEx[]; muscles: Record<string, number> }>("/api/training/today"),
        year: loadYear(TODAY.getFullYear()),
        prev: TODAY.getMonth() < 3 ? loadYear(TODAY.getFullYear() - 1) : Promise.resolve(),
        recs: api("/api/training/recommendations"),
        recent: api<{ items: any[] }>(`/api/training/exercises/recent?locale=${LANG}`),
    });
    S.plan = (r.plans || []).find((p: any) => p.is_active) || null;
    await loadWeek();
    const d = todayDay();
    S.today = d && !d.rest ? r.today?.exercises || [] : [];
    S.muscles = d && !d.rest ? r.today?.muscles || {} : {};
    S.recs = r.recs;
    S.recent = r.recent?.items || [];
    S.loaded = true;
    render();
    if (first) openFromHash((name, arg) => (name === "plan" ? void openPlanEditor() : openSheet(name, arg)));
}

mount(page);
void load();
