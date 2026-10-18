"use strict";
// Admin analytics page. All text is set with textContent / SVG attributes
// (no innerHTML), and the data endpoint returns aggregates only.
const SVG_NS = "http://www.w3.org/2000/svg";
const YELLOW = "#ffd43b";
const VIOLET = "#9b5de5";
function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className)
        node.className = className;
    if (text !== undefined)
        node.textContent = text;
    return node;
}
const fmt = (n) => n === null || n === undefined ? "—" : n.toLocaleString("uk-UA");
const pct = (r) => (r === null ? "—" : `${Math.round(r * 100)}%`);
function stat(value, label, hint) {
    const box = el("div", "adm-stat");
    box.append(el("div", "adm-stat-value", value), el("div", "adm-stat-label", label));
    if (hint)
        box.append(el("div", "adm-stat-hint", hint));
    return box;
}
function chart(target, points, color, granularity) {
    target.replaceChildren();
    if (!points.length || points.every((p) => p.value === 0)) {
        target.append(el("p", "adm-empty", "Немає даних за цей період"));
        return;
    }
    const w = 320, h = 140, padL = 28, padB = 18, padT = 8;
    const max = Math.max(...points.map((p) => p.value), 1);
    const bw = (w - padL) / points.length;
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("class", "adm-chart");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Графік за ${granularity === "week" ? "тижнями" : "днями"}`);
    const label = (x, y, text, anchor) => {
        const t = document.createElementNS(SVG_NS, "text");
        t.setAttribute("x", String(x));
        t.setAttribute("y", String(y));
        t.setAttribute("class", "axis");
        t.setAttribute("text-anchor", anchor);
        t.textContent = text;
        svg.append(t);
    };
    label(0, padT + 8, String(max), "start");
    label(0, h - padB, "0", "start");
    points.forEach((p, i) => {
        const bh = ((h - padB - padT) * p.value) / max;
        const rect = document.createElementNS(SVG_NS, "rect");
        rect.setAttribute("x", String(padL + i * bw + 0.5));
        rect.setAttribute("y", String(h - padB - bh));
        rect.setAttribute("width", String(Math.max(bw - 1, 1)));
        rect.setAttribute("height", String(bh));
        rect.setAttribute("fill", color);
        const title = document.createElementNS(SVG_NS, "title");
        title.textContent = `${p.date}: ${p.value}`;
        rect.append(title);
        svg.append(rect);
    });
    label(padL, h - 4, points[0].date.slice(5), "start");
    label(w, h - 4, points[points.length - 1].date.slice(5), "end");
    target.append(svg);
}
const $ = (id) => document.getElementById(id);
function render(data) {
    $("adm-period").textContent =
        `${data.start} — ${data.end} (UTC), ${data.granularity === "week" ? "по тижнях" : "по днях"}`;
    const u = data.users;
    $("adm-users").replaceChildren(stat(fmt(u.total), "Усього користувачів"), stat(fmt(u.new_in_period), "Нових за період"), stat(fmt(u.premium), "Преміум"), stat(fmt(u.with_telegram), "З Telegram"));
    chart($("chart-registrations"), u.registrations, YELLOW, data.granularity);
    const t = data.tracked;
    const badge = $("adm-tracked-badge");
    badge.className = "adm-badge is-exact";
    if (!t.available) {
        badge.textContent = "ще немає даних";
        $("adm-tracked-note").textContent =
            "Трекінг активності щойно ввімкнено: DAU/WAU/MAU та retention з'являться після перших дій користувачів. Історичну активність відновити неможливо.";
        $("adm-tracked").hidden = true;
    }
    else {
        badge.textContent = `точні, з ${t.tracking_since}`;
        $("adm-tracked-note").textContent =
            "Активний користувач = виконав хоча б одну успішну дію (їжа, вода, вага, тренування, сон, звичка) цього дня. Перегляди сторінок не рахуються." +
                (t.covers_whole_period ? "" : " Період починається раніше за трекінг — показники неповні.");
        $("adm-tracked").hidden = false;
        $("adm-active").replaceChildren(stat(fmt(t.dau), "DAU", "активні сьогодні"), stat(fmt(t.wau), "WAU", "останні 7 днів"), stat(fmt(t.mau), "MAU", "останні 30 днів"), stat(fmt(t.avg_active_days_per_user), "Активних днів на користувача", "за період"), stat(fmt(t.new), "Нові", "перша дія в цьому періоді"), stat(fmt(t.returning), "Поверталися", "були активні раніше"), stat(fmt(t.unknown), "Невідомо", "зареєстровані до запуску трекінгу: попередня активність не записана"), stat(fmt(t.active_users_by_source?.web ?? 0), "Активні через сайт"), stat(fmt(t.active_users_by_source?.telegram ?? 0), "Активні через Telegram"));
        $("adm-active-title").textContent =
            data.granularity === "week" ? "Активні користувачі по тижнях" : "Активні користувачі по днях";
        chart($("chart-active"), t.active_series ?? [], VIOLET, data.granularity);
        const r = t.retention;
        const cell = (label, d) => stat(pct(d.rate), label, `${d.retained} із ${d.cohort}`);
        $("adm-retention").replaceChildren(cell("День 1", r.day1), cell("День 7", r.day7), cell("День 30", r.day30), stat(pct(r.returned.rate), "Повернулися хоч раз", `${r.returned.returned} із ${r.returned.cohort}`));
        $("adm-retention-note").textContent =
            "Когорта: користувачі, зареєстровані після запуску трекінгу, чия перша дія припала на період. День N: активні рівно через N днів після першої дії; враховуються лише ті, у кого цей день уже настав. Мала когорта дає нестабільні відсотки.";
    }
    const features = $("adm-features");
    features.replaceChildren();
    for (const f of data.features.items) {
        const card = el("div", "adm-card");
        const head = el("div", "adm-feature-head");
        head.append(el("h3", undefined, f.label), el("strong", undefined, fmt(f.records)));
        const meta = el("p", "adm-feature-meta", `${fmt(f.users)} користувачів · ${f.records_per_user ?? "—"} записів на користувача · охоплення ${pct(f.reach)}`);
        if (f.trend === "declining" || f.trend === "growing") {
            const span = el("span", `adm-trend-${f.trend}`, f.trend === "declining" ? " ▼ спад" : " ▲ зростання");
            span.title = `Попередній період: ${f.previous_records}`;
            meta.append(span);
        }
        const bar = el("div", "adm-bar");
        const fill = document.createElement("span");
        fill.style.width = `${Math.round((f.reach ?? 0) * 100)}%`;
        bar.append(fill);
        const chartBox = el("div");
        card.append(head, meta, bar, chartBox);
        features.append(card);
        chart(chartBox, f.series, VIOLET, data.granularity);
    }
    const summary = $("adm-summary");
    summary.replaceChildren();
    const items = data.features.items;
    const used = items.filter((f) => f.records > 0).sort((a, b) => b.users - a.users);
    const add = (text) => summary.append(el("li", undefined, text));
    add(`Користувачів: ${fmt(u.total)}, нових за період: ${fmt(u.new_in_period)}.`);
    if (used.length) {
        add(`Найбільше охоплення: ${used.slice(0, 3).map((f) => `${f.label} (${fmt(f.users)})`).join(", ")}.`);
    }
    else {
        add("За період немає записів у жодній функції.");
    }
    const declining = items.filter((f) => f.trend === "declining");
    if (declining.length)
        add(`Спад проти попереднього періоду: ${declining.map((f) => f.label).join(", ")}.`);
    const low = items.filter((f) => f.records === 0);
    if (low.length)
        add(`Без записів за період: ${low.map((f) => f.label).join(", ")}.`);
}
async function load(range) {
    const root = $("adm");
    $("adm-loading").hidden = false;
    $("adm-error").hidden = true;
    $("adm-content").hidden = true;
    try {
        const res = await fetch(`${root.dataset.url}?range=${encodeURIComponent(range)}`, {
            headers: { Accept: "application/json" },
            credentials: "same-origin",
        });
        if (!res.ok)
            throw new Error(String(res.status));
        render((await res.json()));
        $("adm-content").hidden = false;
    }
    catch {
        const err = $("adm-error");
        err.textContent = "Не вдалося завантажити аналітику. Спробуйте оновити або увійдіть знову.";
        err.hidden = false;
    }
    finally {
        $("adm-loading").hidden = true;
    }
}
let current = "30";
document.querySelectorAll(".adm-range").forEach((button) => {
    button.addEventListener("click", () => {
        current = button.dataset.range ?? "30";
        document.querySelectorAll(".adm-range").forEach((b) => b.classList.remove("is-active"));
        button.classList.add("is-active");
        void load(current);
    });
});
$("adm-refresh").addEventListener("click", () => void load(current));
void load(current);
