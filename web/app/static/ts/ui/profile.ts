// Profile tab: who you are, language, goals, account, the other sections of the app,
// and a month heatmap of how many modules were logged each day.

import {
    mount, render, api, loadAll, defineSheets, defineActions, head, doneFoot, tipCard, heatCard, Tip,
    t, form, I, esc, fmtN, U, LANG, TK, liters, kg, dur, monthKeys, monthsBack, openSheet,
} from "./core.js";
import { defineDaySheet, openFromHash } from "./common.js";
import { showStreak, streakOf } from "./shell.js";

interface HeatDay { date: string; nutrition: { calories: number }; recovery: { sleep_hours: number }; training: { completed: boolean }; }
interface User { name: string; goal: string; weight: number | null; premium: boolean; logout: string; }

const USER: User = (() => {
    try { return JSON.parse(document.getElementById("ux-user")?.textContent || "{}"); } catch { return {} as User; }
})();
const LANGS: [string, string][] = [["uk", "Українська"], ["en", "English"], ["pl", "Polski"], ["ru", "Русский"]];
const S: { heat: Record<string, HeatDay>; off: number; day?: any; stats?: any; streak: number } = { heat: {}, off: 0, streak: 0 };

const logged = (k: string): number => {
    const h = S.heat[k];
    if (!h) return 0;
    return (h.training.completed ? 1 : 0) + (h.nutrition.calories > 0 ? 1 : 0) + (h.recovery.sleep_hours > 0 ? 1 : 0);
};
const level = (k: string): number => [0, 2, 3, 4][logged(k)];

function tips(): Tip[] {
    const out: Tip[] = [];
    const trend = S.stats?.weight_trend_detail;
    if (S.day && S.day.goals_available === false)
        out.push({ c: "var(--good)", icon: "target", t: t("tips.goalsT"), d: t("tips.goalsD"), href: "/profile/account", cta: t("cta.params") });
    if (trend && Math.abs(trend.change_kg || 0) >= 1)
        out.push({ c: "var(--good)", icon: "scale", t: t("tips.goalT"), d: t("tips.goalD", { kg: kg(Math.abs(trend.change_kg)) }), href: "/profile/account", cta: t("cta.params") });
    if (S.streak >= 2) out.push({ c: "var(--streak)", icon: "fire", t: t("tips.streakT", { n: fmtN(S.streak) }), d: t("tips.streakD"), href: "/dashboard/", cta: t("cta.home") });
    out.push({ c: "var(--good)", icon: "scale", t: t("tips.weighT"), d: t("tips.weighD"), href: "/nutrition/#sheet:weight", cta: t("cta.weight") });
    return out;
}

function page() {
    const d = S.day;
    const goalV = d?.kcal_goal ? `${fmtN(d.kcal_goal)} ${U("kcal")}${d.water_goal ? ` · ${liters(d.water_goal)}` : ""}` : t("me.noGoals");
    const user = `<section class="w user">
      <span class="ava" aria-hidden="true">${esc((USER.name || "?").charAt(0).toUpperCase())}</span>
      <div class="user-b"><b>${esc(USER.name)}</b><span>${USER.goal ? t("me.goal", { goal: esc(USER.goal) }) : t("me.noGoal")}${USER.weight ? ` · ${kg(USER.weight)}` : ""}</span></div>
      <a class="ux-chip pro" href="/premium">${I("crown")}${USER.premium ? "PRO" : t("me.getPro")}</a>
    </section>`;
    const set = `<section class="w set auto">
      <button type="button" class="set-row" data-open="lang">${I("globe")}<span class="set-l">${t("me.lang")}</span><span class="set-v">${LANGS.find(([c]) => c === LANG)?.[1] || ""}</span>${I("next")}</button>
      <button type="button" class="set-row" data-open="goals">${I("target")}<span class="set-l">${t("me.goals")}</span><span class="set-v">${goalV}</span>${I("next")}</button>
      <a class="set-row" href="/profile/account">${I("shield")}<span class="set-l">${t("me.account")}</span><span class="set-v">${t("me.accountV")}</span>${I("next")}</a>
      <button type="button" class="set-row" data-open="more">${I("grid")}<span class="set-l">${t("me.more")}</span><span class="set-v">${t("me.moreV")}</span>${I("next")}</button>
    </section>`;
    const mk = monthKeys(S.off);
    const active = mk.filter((k) => logged(k) > 0).length;
    const first = Object.keys(S.heat).sort().find((k) => logged(k) > 0) || null;
    const heat = heatCard({
        off: S.off, minOff: monthsBack(first), color: "var(--rec)", label: t("heat.me"), level, mod: "me",
        stats: [[fmtN(active), form("st.activeDays", active)], [fmtN(S.streak), form("st.streak", S.streak)]],
        legend: [t("heat.lg.me.0"), t("heat.lg.me.1")],
    });
    return { cls: "pg-me", html: user + set + heat + tipCard(tips()) };
}

defineDaySheet();
defineSheets({
    lang: () => ({
        c: "var(--rec)",
        html: head(t("me.lang"), "") + `<div class="sh-b"><div class="langs" role="radiogroup" aria-label="${esc(t("me.lang"))}">${LANGS.map(([c, n]) => `<button type="button" role="radio" lang="${c}" aria-checked="${c === LANG}" data-act="lang" data-v="${c}"><span>${n}</span>${c === LANG ? I("check") : ""}</button>`).join("")}</div></div>`,
    }),
    goals() {
        const d = S.day || {};
        const rows: [string, string, string, string][] = [
            ["food", "var(--food)", t("tile.kcal"), d.kcal_goal ? `${fmtN(d.kcal_goal)} ${U("kcal")}` : "—"],
            ["egg", "var(--protein)", t("tile.protein"), d.protein_goal ? `${fmtN(d.protein_goal)} ${U("g")}` : "—"],
            ["drop", "var(--water)", t("tile.water"), d.water_goal ? liters(d.water_goal) : "—"],
            ["moon", "var(--sleep)", t("tile.sleep"), dur(480)],
        ];
        return {
            c: "var(--good)",
            html: head(t("me.goals"), t("me.goalsSub")) + `<div class="sh-b"><ul class="dl">${rows.map(([i, c, l, v]) => `<li><span class="ico" style="--c:${c}">${I(i)}</span><span class="dl-b"><b>${l}</b></span><span class="dl-v">${v}</span></li>`).join("")}</ul>
              <a class="btn ghost" href="/profile/account">${I("edit")}<span>${t("cta.params")}</span></a></div>` + doneFoot(),
        };
    },
    more: () => {
        const links: [string, string, string][] = [
            ["/training/#sheet:plan", "list", "more.plan"], ["/equipment/", "train", "more.equipment"], ["/tracker/", "grid", "more.tracker"],
            ["/premium", "crown", "more.premium"], ["/about?layout=app", "rec", "more.about"], ["/info?layout=app", "shield", "more.info"],
        ];
        return {
            c: "var(--rec)", dayw: true,
            html: head(t("me.more"), "") + `<div class="sh-b"><ul class="dl">${links.map(([h, i, k]) => `<li><a class="set-row" href="${h}"><span class="ico" style="--c:var(--rec)">${I(i)}</span><span class="set-l">${t(k)}</span>${I("next")}</a></li>`).join("")}</ul>
              <a class="btn ghost" href="${esc(USER.logout || "/auth/logout")}">${I("logout")}<span>${t("me.logout")}</span></a></div>` + doneFoot(),
        };
    },
});
defineActions({
    mon(el) { S.off += Number(el.dataset.d); render(); },
    lang(el) {
        const secure = location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `nosifit_locale=${encodeURIComponent(el.dataset.v || "en")}; Path=/; Max-Age=${60 * 60 * 24 * 365}; SameSite=Lax${secure}`;
        location.reload();
    },
});

async function load(): Promise<void> {
    const r = await loadAll({
        heat: api<{ days: HeatDay[] }>("/api/dashboard/heatmap"),
        day: api(`/api/nutrition/day?locale=${LANG}`),
        stats: api("/api/nutrition/stats?days=30"),
    });
    for (const h of r.heat?.days || []) S.heat[h.date] = h;
    S.streak = streakOf(r.heat?.days || [], TK);
    showStreak(S.streak);
    S.day = r.day;
    S.stats = r.stats;
    render();
    openFromHash(openSheet);
}

mount(page);
void load();
