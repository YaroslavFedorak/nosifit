// Recovery tab: last night's sleep, muscle readiness on the body map, a short stretch,
// the month sleep heatmap and tips.
import { mount, render, api, loadAll, defineSheets, defineActions, openSheet, closeSheet, drawSheet, onSheetClose, toast, head, saveFoot, tipCard, heatCard, t, tn, form, I, esc, fmtN, TK, TODAY, addDays, key, dayShort, lastDays, dayLabels, pad, clock, dur, durHtml, signed, chart, figure, crop, MUSCLE_PARTS, STATUS, stepper, monthKeys, monthsBack, avg, } from "./core.js";
import { defineDaySheet, openFromHash } from "./common.js";
import { showStreak, streakOf } from "./shell.js";
const UID = document.body.dataset.uid || "";
const GOAL = 480;
const READY = { low: "low", moderate: "mod", ready: "ready", recovered: "full" };
const STRETCH = [
    { id: "calf", m: "calves", sec: 60 }, { id: "ham", m: "hamstrings", sec: 60 },
    { id: "pigeon", m: "glutes", sec: 60 }, { id: "quad", m: "quads", sec: 60 },
];
const ST_MIN = Math.round(STRETCH.reduce((s, x) => s + x.sec, 0) / 60);
const S = {
    sleep: null, heat: {}, status: {}, off: 0, muscle: null, draft: null,
    habit: { id: null, userHabitId: null, done: false }, st: { i: 0, left: STRETCH[0].sec, run: false },
};
const minutesOf = (iso) => { const d = new Date(iso); return d.getHours() * 60 + d.getMinutes(); };
const sleepH = (k) => S.heat[k]?.recovery.sleep_hours || 0;
const level = (k) => { const h = sleepH(k); return !h ? 0 : h >= 8 ? 4 : h >= 7 ? 3 : h >= 6 ? 2 : 1; };
const weekDebt = () => lastDays(7).reduce((s, k) => (sleepH(k) ? s + Math.max(0, GOAL - sleepH(k) * 60) : s), 0);
const bedtime = () => {
    if (!S.sleep?.wake_time)
        return null;
    return minutesOf(S.sleep.wake_time) - GOAL - (weekDebt() >= 60 ? 30 : 0) + 1440;
};
const statusOf = (m) => READY[S.status[m]?.readiness || ""] || "none";
// The muscle a body part belongs to, among the muscles the model reports.
const muscleOfPart = (part) => {
    if (S.status[part])
        return part;
    return Object.keys(S.status).find((m) => (MUSCLE_PARTS[m] || []).includes(part)) || null;
};
const partColor = (part) => {
    const m = muscleOfPart(part);
    return m ? STATUS[statusOf(m)] : null;
};
const zone = (ok, group) => group.some((m) => S.status[m] && ok(statusOf(m)));
const LEGS = ["quads", "hamstrings", "glutes", "calves", "adductors"];
const UPPER = ["chest", "lats", "upper-back", "shoulders", "biceps", "triceps"];
function tips() {
    const out = [];
    const bed = bedtime(), debt = Math.round(weekDebt());
    if (bed != null && debt >= 30)
        out.push({ c: "var(--sleep)", icon: "moon", t: t("tips.bedT", { time: clock(bed) }), d: t("tips.bedD", { debt: dur(debt) }), open: "sleep", cta: t("cta.sleep") });
    if (!S.habit.done)
        out.push({ c: "var(--mob)", icon: "stretch", t: t("tips.stretchT", { min: fmtN(ST_MIN) }), d: t("tips.stretchD"), open: "stretch", cta: t("cta.stretch") });
    const tired = Object.values(S.status).filter((s) => s.readiness === "low" || s.readiness === "moderate").sort((a, b) => a.readiness_score - b.readiness_score)[0];
    if (tired)
        out.push({ c: "var(--r-mod)", icon: "body", t: t("tips.restT", { m: t("mus." + tired.muscle) }), d: t("tips.restD"), open: "muscle", arg: tired.muscle, cta: t("cta.muscle") });
    if (!S.sleep?.duration_minutes)
        out.push({ c: "var(--sleep)", icon: "moon", t: t("tips.logSleepT"), d: t("tips.logSleepD"), open: "sleep", cta: t("cta.sleep") });
    return out;
}
function page() {
    const ln = S.sleep, debt = Math.round(weekDebt()), bed = bedtime();
    const T0 = 20 * 60, SPAN = 14 * 60;
    const pos = (m) => (((m - T0 + 1440) % 1440) / SPAN) * 100;
    const ticks = [22, 0, 2, 4, 6, 8].map((h) => ({ h, x: pos(h * 60) }));
    const has = !!(ln && ln.duration_minutes && ln.bedtime);
    const b0 = has ? minutesOf(ln.bedtime) : 0;
    const hero = `<section class="w hero sl" style="--c:var(--sleep)">
      <div class="h-top"><span class="eyebrow">${t("sleep.lastNight")}</span><button type="button" class="btn sm ghost" data-open="sleep">${I(has ? "edit" : "plus")}<span>${has ? t("common.edit") : t("sleep.log")}</span></button></div>
      <div class="sl-dur">${has ? durHtml(ln.duration_minutes) : `<b>—</b>`}</div>
      ${has ? `<div class="sl-times"><span>${I("moon")}${clock(b0)}</span><span>${I("sun")}${clock(b0 + ln.duration_minutes)}</span><span class="muted">${t("sleep.goal", { v: dur(GOAL) })}</span></div>
      <div class="tline" aria-hidden="true"><div class="tl-bar">${ticks.map((x) => `<i style="left:${x.x}%"></i>`).join("")}<span style="left:${pos(b0)}%;width:${Math.min(100 - pos(b0), (ln.duration_minutes / SPAN) * 100)}%"></span></div><div class="tl-x">${ticks.map((x) => `<span style="left:${x.x}%">${pad(x.h)}:00</span>`).join("")}</div></div>`
        : `<div class="sl-times"><span class="muted">${t("sleep.none")}</span></div>`}
      ${bed != null ? `<button type="button" class="sl-tip" data-open="sleep"><span class="ico">${I("bell")}</span><span><b>${t("sleep.tonight", { time: clock(bed) })}</b><span>${debt ? t("sleep.debt", { v: dur(debt) }) : t("sleep.noDebt")}</span></span>${I("next")}</button>` : ""}
    </section>`;
    const legsTired = zone((s) => s === "low" || s === "mod", LEGS), upperReady = zone((s) => s === "ready" || s === "full", UPPER);
    const restingZone = legsTired ? t("body.legs") : zone((s) => s === "low" || s === "mod", UPPER) ? t("body.upper") : t("body.nothing");
    const readyZone = upperReady ? t("body.upper") : zone((s) => s === "ready" || s === "full", LEGS) ? t("body.legs") : t("body.nothing");
    const side = `<section class="w side bod" style="--c:var(--mob)"><div class="bod-in">
      <button type="button" class="figfit" data-open="muscle" aria-label="${esc(t("body.title"))}">${figure("ante", { color: partColor })}${figure("post", { color: partColor })}</button>
      <div class="bod-i">
        <div class="bod-st"><i style="--d:var(--r-mod)"></i><span>${t("body.resting")}: <b>${restingZone}</b></span></div>
        <div class="bod-st"><i style="--d:var(--r-full)"></i><span>${t("body.ready")}: <b>${readyZone}</b></span></div>
        <div class="crops">${STRETCH.map((s) => `<span class="crop">${crop(s.m, "var(--mob)")}</span>`).join("")}</div>
        <button type="button" class="btn sm" data-open="stretch">${I(S.habit.done ? "check" : "play")}<span>${S.habit.done ? t("st2.again") : t("st2.start", { min: fmtN(ST_MIN) })}</span></button>
      </div>
    </div></section>`;
    const mk = monthKeys(S.off);
    const nights = mk.filter((k) => sleepH(k) > 0);
    const n7 = nights.filter((k) => sleepH(k) >= 7).length;
    const first = Object.keys(S.heat).sort().find((k) => sleepH(k) > 0) || null;
    const heat = heatCard({
        off: S.off, minOff: monthsBack(first), color: "var(--sleep)", label: t("heat.rec"), level, mod: "rec",
        stats: [[nights.length ? dur(avg(nights.map((k) => sleepH(k) * 60))) : "—", t("st.avgSleep")], [fmtN(n7), form("st.nights7", n7)]],
        legend: [t("heat.lg.rec.0"), t("heat.lg.rec.1")],
    });
    return { cls: "pg-mod", html: hero + side + heat + tipCard(tips()) };
}
/* ---------- Sheets ---------- */
defineDaySheet();
defineSheets({
    sleep() {
        if (!S.draft) {
            const ln = S.sleep;
            S.draft = ln?.bedtime && ln.wake_time ? { bed: minutesOf(ln.bedtime), wake: minutesOf(ln.wake_time) } : { bed: 23 * 60, wake: 7 * 60 };
        }
        const d = S.draft, du = ((d.wake - d.bed + 1440) % 1440) || 1440;
        const week = lastDays(7);
        return {
            c: "var(--sleep)", wide: true,
            html: head(t("tile.sleep"), `${t("sleep.lastNight")} · ${dayShort(TODAY)}`) + `<div class="sh-b"><div class="wo-grid"><div class="wo-col">
              <div class="stp-row"><span class="ico" style="--c:var(--sleep)">${I("moon")}</span><span class="stp-l"><b>${t("sleep.bed")}</b></span>${stepper("slBed", clock(d.bed), t("sleep.bed"))}</div>
              <div class="stp-row"><span class="ico" style="--c:var(--train)">${I("sun")}</span><span class="stp-l"><b>${t("sleep.wake")}</b></span>${stepper("slWake", clock(d.wake), t("sleep.wake"))}</div>
              <div class="kv" style="--n:2"><div><b>${dur(du)}</b><span>${t("sleep.dur")}</span></div><div><b>${signed(du - GOAL, dur)}</b><span>${t("sleep.vsGoal")}</span></div></div>
            </div><div class="wo-col"><p class="ch-t">${t("sleep.week")}</p>${chart(week.map((k) => sleepH(k) || null), 10, dayLabels(week), "var(--sleep)")}</div></div></div>` + saveFoot("slSave"),
        };
    },
    muscle(arg) {
        if (arg && S.status[arg])
            S.muscle = arg;
        if (!S.muscle || !S.status[S.muscle]) {
            const sorted = Object.values(S.status).sort((a, b) => a.readiness_score - b.readiness_score);
            S.muscle = sorted[0]?.muscle || null;
        }
        const x = S.muscle ? S.status[S.muscle] : null;
        const act = (part) => muscleOfPart(part);
        const card = x
            ? `<div class="ms-card" style="--d:${STATUS[statusOf(x.muscle)]}"><h4>${t("mus." + x.muscle)}</h4><span class="st"><i></i>${t("status." + statusOf(x.muscle))}</span>
                <p>${t("mstate." + x.state)} ${tn("mus2.sets", Math.round(x.weekly_sets))}</p></div>`
            : `<p class="fl-empty">${t("body.noData")}</p>`;
        return {
            c: "var(--mob)", wide: true, tall: true,
            html: head(t("body.title"), t("body.hint")) + `<div class="sh-b"><div class="ms">
              <div class="ms-figs figfit">${figure("ante", { color: partColor, act, sel: S.muscle })}${figure("post", { color: partColor, act, sel: S.muscle })}</div>
              <div class="ms-i">${card}
                <div class="legend">${["low", "mod", "ready", "full"].map((s) => `<span style="--d:${STATUS[s]}"><i></i>${t("status." + s)}</span>`).join("")}</div>
                <button type="button" class="btn" style="--c:var(--mob)" data-open="stretch">${I("play")}<span>${t("st2.start", { min: fmtN(ST_MIN) })}</span></button>
              </div></div></div>`,
        };
    },
    stretch() {
        const st = S.st, s = STRETCH[st.i];
        onSheetClose(stopTimer);
        return {
            c: "var(--mob)",
            html: head(t("st2.title"), t("wo.exOf", { a: st.i + 1, b: STRETCH.length })) + `<div class="sh-b">
              <div class="wo-prog" style="--train:var(--mob)">${STRETCH.map((_, i) => `<i class="${i === st.i ? "on" : i < st.i ? "done" : ""}"></i>`).join("")}</div>
              <div class="pl"><span class="crop">${crop(s.m, "var(--mob)")}</span><div class="pl-r"><h4>${t("sx." + s.id)}</h4><p class="pl-m">${t("sx." + s.id + "D")}</p>
                <div class="pl-t" id="pl-t">${Math.floor(st.left / 60)}:${pad(st.left % 60)}</div>
                <div class="pl-c"><button type="button" class="ib" data-act="stGo" data-d="-1" aria-label="${esc(t("common.back"))}" ${st.i === 0 ? "disabled" : ""}>${I("prev")}</button><button type="button" class="play" data-act="stPlay" aria-label="${esc(st.run ? t("st2.pause") : t("st2.play"))}">${I(st.run ? "pause" : "play")}</button><button type="button" class="ib" data-act="stGo" data-d="1" aria-label="${esc(t("common.next"))}">${I("next")}</button></div>
              </div></div>
            </div>`,
        };
    },
});
let timer = 0;
function stopTimer() {
    if (timer) {
        clearInterval(timer);
        timer = 0;
    }
    S.st.run = false;
}
async function stretchDone() {
    stopTimer();
    S.st = { i: 0, left: STRETCH[0].sec, run: false };
    closeSheet();
    try {
        if (!S.habit.userHabitId && S.habit.id) {
            const r = await api(`/api/recovery/habits/add/${S.habit.id}`, { method: "POST" });
            S.habit.userHabitId = r.user_habit_id;
        }
        if (S.habit.userHabitId && !S.habit.done)
            await api("/api/recovery/habits/logs", { method: "POST", body: { user_habit_id: S.habit.userHabitId } });
        S.habit.done = true;
        toast(t("st2.done"));
    }
    catch {
        toast(t("err.save"));
    }
    render();
}
defineActions({
    mon(el) { S.off += Number(el.dataset.d); render(); },
    slBed(el) { if (S.draft) {
        S.draft.bed = (S.draft.bed + 15 * Number(el.dataset.d) + 1440) % 1440;
        drawSheet();
    } },
    slWake(el) { if (S.draft) {
        S.draft.wake = (S.draft.wake + 15 * Number(el.dataset.d) + 1440) % 1440;
        drawSheet();
    } },
    async slSave() {
        const d = S.draft;
        if (!d)
            return;
        const wakeDay = TODAY;
        const bedDay = d.bed > d.wake ? addDays(TODAY, -1) : TODAY;
        const iso = (day, m) => `${key(day)}T${clock(m)}:00`;
        try {
            await api("/api/recovery/sleep", { method: "POST", body: { sleep_start: iso(bedDay, d.bed), sleep_end: iso(wakeDay, d.wake) } });
            S.draft = null;
            closeSheet();
            toast(t("common.saved"));
            await loadSleep();
            render();
        }
        catch {
            toast(t("err.save"));
        }
    },
    mus(el) { S.muscle = el.dataset.m || null; drawSheet(); },
    stGo(el) {
        const ni = S.st.i + Number(el.dataset.d);
        if (ni >= STRETCH.length) {
            void stretchDone();
            return;
        }
        S.st.i = Math.max(0, ni);
        S.st.left = STRETCH[S.st.i].sec;
        drawSheet();
    },
    stPlay() {
        const st = S.st;
        if (st.run) {
            stopTimer();
            drawSheet();
            return;
        }
        st.run = true;
        timer = window.setInterval(() => {
            st.left--;
            if (st.left <= 0) {
                if (st.i < STRETCH.length - 1) {
                    st.i++;
                    st.left = STRETCH[st.i].sec;
                    drawSheet();
                }
                else
                    void stretchDone();
                return;
            }
            const el = document.getElementById("pl-t");
            if (el)
                el.textContent = `${Math.floor(st.left / 60)}:${pad(st.left % 60)}`;
        }, 1000);
        drawSheet();
    },
});
/* ---------- Data ---------- */
async function loadSleep() {
    const [day, heat] = await Promise.all([
        api(`/api/recovery/day-details/${UID}?date=${TK}`),
        api("/api/dashboard/heatmap"),
    ]);
    S.sleep = day.sleep;
    for (const h of heat.days)
        S.heat[h.date] = h;
    showStreak(streakOf(heat.days, TK));
}
async function load() {
    const r = await loadAll({
        sleep: loadSleep(),
        recs: api("/api/training/recommendations"),
        habits: api("/api/recovery/habits/list"),
        mine: api(`/api/recovery/habits/user/${UID}`),
    });
    for (const m of r.recs?.muscle_status || [])
        S.status[m.muscle] = m;
    S.guidance = r.recs?.guidance;
    S.habit.id = (r.habits || []).find((h) => h.slug === "stretching")?.id ?? null;
    const mine = (r.mine || []).find((h) => h.slug === "stretching");
    S.habit.userHabitId = mine?.user_habit_id ?? mine?.id ?? null;
    S.habit.done = !!mine?.completed;
    render();
    openFromHash(openSheet);
}
mount(page);
void load();
