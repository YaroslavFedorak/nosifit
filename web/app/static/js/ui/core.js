// Shared kit of the five main tabs: translations, formatting, icons, small charts,
// the body map, sheets, toasts, the month heatmap card and the tip card.
// Pages render HTML strings; delegated listeners route [data-act] and [data-open].
import { BODY } from "./body.js";
/* ---------- DOM and dates ---------- */
export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
export const pad = (n) => String(n).padStart(2, "0");
export const key = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const parse = (k) => {
    const [y, m, d] = k.slice(0, 10).split("-").map(Number);
    return new Date(y, m - 1, d);
};
export const addDays = (d, n) => {
    const x = new Date(d);
    x.setDate(x.getDate() + n);
    return x;
};
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const sum = (a) => a.reduce((s, v) => s + v, 0);
export const avg = (a) => (a.length ? sum(a) / a.length : 0);
export const mondayOf = (d) => addDays(d, -((d.getDay() + 6) % 7));
// "Today" is the server's calendar day (APP_TIMEZONE), not the device's.
export const TODAY = parse(document.body.dataset.today || key(new Date()));
export const TK = key(TODAY);
const LOC = { uk: "uk-UA", en: "en-GB", pl: "pl-PL", ru: "ru-RU" };
export const LANG = (document.documentElement.lang || "en").slice(0, 2);
const readJSON = (id) => {
    try {
        return JSON.parse(document.getElementById(id)?.textContent || "{}");
    }
    catch {
        return {};
    }
};
const L = readJSON("ux-i18n");
const PR = new Intl.PluralRules(LOC[LANG] || "en-GB");
export const get = (path, d = L) => path.split(".").reduce((o, k) => (o && typeof o === "object" ? o[k] : undefined), d);
const fill = (s, v) => v ? s.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? String(v[k]) : m)) : s;
export const t = (path, v) => {
    const s = get(path);
    return typeof s === "string" ? fill(s, v) : path;
};
export const form = (path, n) => {
    const f = get(path);
    if (!Array.isArray(f))
        return path;
    const c = PR.select(n);
    return f.length === 2 ? f[c === "one" ? 0 : 1] : f[c === "one" ? 0 : c === "few" ? 1 : 2];
};
export const tn = (path, n, v) => fill(form(path, n), { n: fmtN(n), ...(v || {}) });
// Strings of other namespaces the page embeds (exercise names), with a fallback.
export const extra = (path, fallback) => {
    const s = get(path);
    return typeof s === "string" ? s : fallback;
};
const NFC = {};
export const fmtN = (v, d = 0) => {
    const k = String(d);
    if (!NFC[k])
        NFC[k] = new Intl.NumberFormat(LOC[LANG] || "en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
    return NFC[k].format(v);
};
export const fmt1 = (v) => fmtN(v, Math.abs(v % 1) > 0.04 ? 1 : 0);
export const U = (k) => t("u." + k);
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const dfmt = (d, o) => new Intl.DateTimeFormat(LOC[LANG] || "en-GB", o).format(d);
export const wdName = (d) => {
    const names = get("wdl");
    return Array.isArray(names) ? names[(d.getDay() + 6) % 7] : dfmt(d, { weekday: "long" });
};
export const dayShort = (d) => dfmt(d, { day: "numeric", month: "long" });
export const dayLong = (d) => cap(t("dayFmt", { w: wdName(d), d: dayShort(d) }));
export const monthName = (d) => cap(dfmt(d, { month: "long" }));
export const wd2 = (i) => {
    const a = get("wd2");
    return Array.isArray(a) ? a[i] : "";
};
export const clock = (m) => {
    const x = ((Math.round(m) % 1440) + 1440) % 1440;
    return `${pad(Math.floor(x / 60))}:${pad(x % 60)}`;
};
const hm = (m) => {
    const r = Math.round(m);
    return [Math.floor(r / 60), r % 60];
};
export const dur = (m) => {
    const [h, mm] = hm(m);
    return h && mm ? `${h} ${U("h")} ${mm} ${U("min")}` : h ? `${h} ${U("h")}` : `${mm} ${U("min")}`;
};
export const durHtml = (m) => {
    const [h, mm] = hm(m);
    return `${h ? `<span class="du"><b>${h}</b><small>${U("h")}</small></span>` : ""}${mm || !h ? `<span class="du"><b>${mm}</b><small>${U("min")}</small></span>` : ""}`;
};
export const litNum = (l) => {
    const ml = Math.round(l * 1000);
    return fmtN(ml / 1000, ml % 1000 === 0 ? 0 : ml % 100 === 0 ? 1 : 2);
};
export const liters = (l) => `${litNum(l)} ${U("l")}`;
export const kg = (v) => `${fmtN(v, 1)} ${U("kg")}`;
export const signed = (v, f) => (v > 0 ? "+" : v < 0 ? "−" : "") + f(Math.abs(v));
/* ---------- Icons ---------- */
const P = {
    home: '<path d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z"/>',
    train: '<path d="M6.5 6.5v11M3.5 9v6M17.5 6.5v11M20.5 9v6M6.5 12h11"/>',
    food: '<path d="M7 3v7a2 2 0 0 0 2 2v9M11 3v7a2 2 0 0 1-2 2M7 3v4M11 3v4M17 21V3c-2.2 1.2-3.3 3.8-3.3 7.5H17"/>',
    rec: '<path d="M20.4 6.6a4.9 4.9 0 0 0-7.5-1.1L12 6.4l-.9-.9a4.9 4.9 0 0 0-7 6.9l7.9 8 7.9-8a4.9 4.9 0 0 0 .5-5.8z"/><path d="M3.5 12.5h4l1.6-3 2.8 6 1.6-3h6.9"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c1.4-3.6 4.2-5.5 7.5-5.5s6.1 1.9 7.5 5.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    minus: '<path d="M5 12h14"/>',
    play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor" stroke="none"/>',
    pause: '<rect x="6.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/>',
    prev: '<path d="M15 6l-6 6 6 6"/>',
    next: '<path d="M9 6l6 6-6 6"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/>',
    drop: '<path d="M12 3.5s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z"/>',
    fire: '<path d="M12 21c3.6 0 6-2.5 6-6 0-3.3-2.2-5.6-3.4-8.5-.4 2-1.4 3.2-2.6 3.8.1-2.8-1-5.3-3.5-7.3.2 3.8-4.5 6.6-4.5 12 0 3.5 2.4 6 6 6z" fill="currentColor" stroke="none"/>',
    egg: '<path d="M12 3c3.6 0 6.5 5.6 6.5 10a6.5 6.5 0 0 1-13 0C5.5 8.6 8.4 3 12 3z"/>',
    scale: '<rect x="3.5" y="3.5" width="17" height="17" rx="4"/><path d="M8 9.5a6 6 0 0 1 8 0l-2.6 2.7a2.2 2.2 0 0 0-2.8 0z"/>',
    walk: '<circle cx="13" cy="4.5" r="1.8"/><path d="M10.5 21l1.5-6-2.5-2.5V9l3-1.5 2.5 3 3 1M9.5 9.5L7 13M12 15l3 6"/>',
    stretch: '<circle cx="13" cy="4.5" r="1.8"/><path d="M4 10.5l5.5-1.5 4 1.5 3-3.5M13.5 10.5l-1.5 5 4.5 5M12 15.5l-5 4.5"/>',
    body: '<circle cx="12" cy="4.5" r="2"/><path d="M5 9l7 1.5L19 9M12 10.5V15l-3 6M12 15l3 6"/>',
    edit: '<path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.6 5.4 3.6 8.5s-1.1 5.9-3.6 8.5c-2.5-2.6-3.6-5.4-3.6-8.5s1.1-5.9 3.6-8.5z"/>',
    target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    band: '<rect x="7.5" y="6.5" width="9" height="11" rx="3"/><path d="M9 6.5L9.5 3h5l.5 3.5M9 17.5l.5 3.5h5l.5-3.5"/>',
    crown: '<path d="M3.5 8l4.5 4 4-6 4 6 4.5-4-2 11h-13z"/>',
    bell: '<path d="M18 8.5a6 6 0 0 0-12 0c0 7-3 8.5-3 8.5h18s-3-1.5-3-8.5M13.7 20.5a2 2 0 0 1-3.4 0"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    trophy: '<path d="M7.5 4h9v5a4.5 4.5 0 0 1-9 0zM7.5 6H4.5a3 3 0 0 0 3 4M16.5 6h3a3 3 0 0 1-3 4M12 13.5V17M8.5 20.5h7M9.5 17h5v3.5h-5z"/>',
    coffee: '<path d="M5 8.5h11v5.5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zM16 10h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5v2M11 3.5v2M14 3.5v2"/>',
    apple: '<path d="M12 7.5c-1.5-1.4-5-1.5-6.2 1.6-1.2 3 .4 7.6 2.5 9.9 1.2 1.3 2.4 1 3.7.4 1.3.6 2.5.9 3.7-.4 2.1-2.3 3.7-6.9 2.5-9.9C17 6 13.5 6.1 12 7.5zM12 7.5c0-2 1-3.5 3-4"/>',
    bowl: '<path d="M3.5 11h17a8.5 8.5 0 0 1-17 0zM9 20h6M8 7.5c0-1.5 1-2 1-3.5M12 7.5c0-1.5 1-2 1-3.5M16 7.5c0-1.5 1-2 1-3.5"/>',
    rest: '<path d="M5 12h14"/>',
    shield: '<path d="M12 3l7.5 3v5.5c0 4.6-3.2 8.2-7.5 9.5-4.3-1.3-7.5-4.9-7.5-9.5V6z"/>',
    grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/><rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
    logout: '<path d="M15 4.5h3a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-3M10 16.5L5.5 12 10 7.5M5.5 12H15"/>',
    scan: '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16M7.5 8v8M10.5 8v8M13.5 8v8M16.5 8v8"/>',
    list: '<path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
};
export const I = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n] || P.plus}</svg>`;
/* ---------- Small charts ---------- */
export const pbar = (r, cls = "") => `<span class="pbar ${cls} ${r > 1.04 ? "over" : ""}"><i style="width:${clamp(r * 100, 0, 100).toFixed(1)}%"></i></span>`;
export const segs = (on, n) => `<span class="segs">${Array.from({ length: n }, (_, i) => `<i class="${i < on ? "on" : ""}"></i>`).join("")}</span>`;
export const mbars = (vals, max) => `<span class="mbars">${vals
    .map((v, i) => `<i class="${i === vals.length - 1 ? "on" : ""}" style="height:${v ? clamp((v / max) * 100, 6, 100).toFixed(1) : 0}%"></i>`)
    .join("")}</span>`;
export const spark = (vals) => {
    if (vals.length < 2)
        return "";
    const lo = Math.min(...vals), hi = Math.max(...vals), sp = hi - lo || 1;
    const pts = vals.map((v, i) => [(i / (vals.length - 1)) * 100, 90 - ((v - lo) / sp) * 80]);
    const [lx, ly] = pts[pts.length - 1];
    return `<span class="spark"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts
        .map((p) => p.map((n) => n.toFixed(1)).join(","))
        .join(" ")}" fill="none" stroke="var(--c)" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"/></svg><i class="spark-dot" style="left:${lx}%;top:${ly}%"></i></span>`;
};
export const lastDays = (n) => Array.from({ length: n }, (_, i) => key(addDays(TODAY, i - n + 1)));
export const dayLabels = (keys) => keys.map((k) => wd2((parse(k).getDay() + 6) % 7));
export const chart = (vals, max, labels, c) => `<div class="chart" style="--c:${c}">${mbars(vals, max)}<div class="ch-x">${labels
    .map((l, i) => `<span class="${i === labels.length - 1 ? "on" : ""}">${esc(l)}</span>`)
    .join("")}</div></div>`;
export const stepper = (act, out, label, attrs = "") => `<span class="stp"><button type="button" data-act="${act}" data-d="-1" ${attrs} aria-label="${esc(t("aria.less"))} ${esc(label)}">${I("minus")}</button><output>${out}</output><button type="button" data-act="${act}" data-d="1" ${attrs} aria-label="${esc(t("aria.more"))} ${esc(label)}">${I("plus")}</button></span>`;
export const STATUS = {
    low: "var(--r-low)", mod: "var(--r-mod)", ready: "var(--r-ready)", full: "var(--r-full)", none: "var(--r-none)",
};
// Muscle ids of the training model, as drawn on the body map.
export const MUSCLE_PARTS = {
    chest: ["chest"], shoulders: ["shoulders"], biceps: ["biceps"], triceps: ["triceps"], forearms: ["forearms"],
    abs: ["abs"], core: ["abs", "obliques"], obliques: ["obliques"], lats: ["lats"], "upper-back": ["upper-back"],
    traps: ["upper-back", "neck"], "lower-back": ["lower-back"], glutes: ["glutes"], quads: ["quads"],
    hamstrings: ["hamstrings"], adductors: ["adductors"], calves: ["calves"],
};
const PART_VIEW = {};
for (const view of ["ante", "post"])
    for (const it of BODY[view])
        if (!PART_VIEW[it.m])
            PART_VIEW[it.m] = view;
const BOX = { ante: [], post: [] };
for (const view of ["ante", "post"]) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const it of BODY[view])
        for (const p of it.p) {
            const n = p.split(" ").map(Number);
            for (let i = 0; i < n.length; i += 2) {
                x0 = Math.min(x0, n[i]);
                x1 = Math.max(x1, n[i]);
                y0 = Math.min(y0, n[i + 1]);
                y1 = Math.max(y1, n[i + 1]);
            }
        }
    BOX[view] = [x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4];
}
const polys = (p) => p.map((x) => `<polygon points="${x}"/>`).join("");
export const figure = (view, o) => {
    const groups = new Map();
    for (const it of BODY[view])
        groups.set(it.m, [...(groups.get(it.m) || []), ...it.p]);
    let out = "";
    for (const [m, p] of groups) {
        const inner = polys(p);
        if (m.startsWith("_")) {
            out += `<g class="np">${inner}</g>`;
            continue;
        }
        const c = o.color(m);
        if (!c) {
            out += `<g class="dim">${inner}</g>`;
            continue;
        }
        const target = o.act ? o.act(m) : null;
        out += target
            ? `<g class="mu act ${o.sel && o.sel === target ? "sel" : ""}" data-act="mus" data-m="${target}" tabindex="0" role="button" aria-label="${esc(t("mus." + target))}" style="--f:${c}">${inner}</g>`
            : `<g class="mu" style="--f:${c}">${inner}</g>`;
    }
    return `<svg viewBox="${BOX[view].map((n) => n.toFixed(1)).join(" ")}" role="img" aria-label="${esc(t(view === "ante" ? "body.front" : "body.back"))}">${out}</svg>`;
};
// A zoomed view of one muscle, used as the icon of an exercise or a stretch.
export const crop = (muscle, color) => {
    const parts = MUSCLE_PARTS[muscle] || [muscle];
    const view = PART_VIEW[parts[0]] || "ante";
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const it of BODY[view])
        if (parts.includes(it.m))
            for (const p of it.p) {
                const n = p.split(" ").map(Number);
                for (let i = 0; i < n.length; i += 2) {
                    x0 = Math.min(x0, n[i]);
                    x1 = Math.max(x1, n[i]);
                    y0 = Math.min(y0, n[i + 1]);
                    y1 = Math.max(y1, n[i + 1]);
                }
            }
    if (x0 > x1)
        return figure(view, { color: () => null });
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const h = Math.max(y1 - y0, (x1 - x0) * 1.15) * 1.9;
    let out = "";
    for (const it of BODY[view])
        out += parts.includes(it.m) ? `<g class="mu" style="--f:${color}">${polys(it.p)}</g>` : `<g class="dim">${polys(it.p)}</g>`;
    return `<svg viewBox="${(cx - h / 2).toFixed(1)} ${(cy - h / 2).toFixed(1)} ${h.toFixed(1)} ${h.toFixed(1)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${out}</svg>`;
};
/* ---------- API ---------- */
export class ApiError extends Error {
    constructor(code, status) {
        super(code);
        this.code = code;
        this.status = status;
    }
}
export async function api(path, opts = {}) {
    let res;
    try {
        res = await fetch(path, {
            method: opts.method || "GET",
            credentials: "same-origin",
            headers: { Accept: "application/json", ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}) },
            body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        });
    }
    catch {
        throw new ApiError("network", 0);
    }
    if (res.status === 401 || (res.redirected && new URL(res.url).pathname.startsWith("/auth/login"))) {
        location.href = "/auth/login";
        throw new ApiError("session_expired", 401);
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok)
        throw new ApiError((data && (data.code || data.error)) || "unknown", res.status);
    return data;
}
// Loads in parallel; a failed request leaves its value undefined instead of failing the page.
export async function loadAll(jobs) {
    const names = Object.keys(jobs);
    const results = await Promise.allSettled(names.map((n) => jobs[n]));
    const out = {};
    let failed = false;
    results.forEach((r, i) => {
        if (r.status === "fulfilled")
            out[names[i]] = r.value;
        else
            failed = true;
    });
    if (failed)
        toast(t("err.load"));
    return out;
}
/* ---------- Toast ---------- */
let toastTimer = 0;
export function toast(msg) {
    const el = $("#ux-toast");
    if (!el)
        return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => el.classList.remove("show"), 2400);
}
/* ---------- Format (phone, short phone, tablet, landscape phone, laptop) ---------- */
export let FORMAT = "f-p";
export function setFormat() {
    const w = innerWidth, h = innerHeight, land = w > h, r = document.documentElement;
    r.classList.remove("f-p", "f-s", "f-t", "f-l", "f-d");
    if (!land)
        r.classList.add(w >= 600 ? "f-t" : "f-p", ...(w < 600 && h < 700 ? ["f-s"] : []));
    else
        r.classList.add(w >= 900 && h >= 521 ? "f-d" : "f-l");
    const f = ["f-d", "f-l", "f-t", "f-p"].find((c) => r.classList.contains(c)) || "f-p";
    const changed = f !== FORMAT;
    FORMAT = f;
    return changed;
}
/* ---------- Fitting ---------- */
function fitHeat(card) {
    const b = $(".ht-b", card), grid = $(".mgrid", card), st = $(".ht-s", card);
    if (!b || !grid || !st)
        return;
    const R = b.getBoundingClientRect();
    if (!R.width || !R.height)
        return;
    const weeks = Number(grid.dataset.weeks || 5), g = clamp(Math.round(Math.min(R.width, R.height) / 45), 2, 5), hd = 13;
    const sw = Math.max(120, R.width * 0.34);
    const cRow = Math.min((R.width - sw - 12 - 6 * g) / 7, (R.height - hd - weeks * g) / weeks);
    b.classList.remove("row");
    const sh = st.getBoundingClientRect().height;
    const cCol = Math.min((R.width - 6 * g) / 7, (R.height - sh - 10 - hd - weeks * g) / weeks);
    const row = cRow > cCol;
    b.classList.toggle("row", row);
    const c = Math.floor(clamp(row ? cRow : cCol, 6, FORMAT === "f-d" ? 72 : 60));
    grid.style.setProperty("--cell", c + "px");
    grid.style.setProperty("--g", g + "px");
    grid.classList.toggle("nums", c >= 20);
    grid.classList.toggle("wide", c >= 19);
    const lg = $(".ht-lg", card);
    if (lg) {
        lg.classList.remove("off");
        if (lg.scrollWidth > st.clientWidth + 0.5 || st.scrollHeight > st.clientHeight + 0.5)
            lg.classList.add("off");
    }
}
function fitFig(box) {
    const svgs = Array.from(box.children).filter((x) => x.tagName.toLowerCase() === "svg");
    const r = box.getBoundingClientRect();
    if (!r.width || !r.height || !svgs.length)
        return;
    const gap = parseFloat(getComputedStyle(box).columnGap) || 0;
    const ars = svgs.map((x) => x.viewBox.baseVal.width / x.viewBox.baseVal.height);
    const h = Math.max(8, Math.min(r.height, (r.width - gap * (svgs.length - 1)) / sum(ars)));
    svgs.forEach((x, i) => {
        x.style.height = h + "px";
        x.style.width = h * ars[i] + "px";
    });
}
const fitEl = (el) => (el.classList.contains("heat") ? fitHeat(el) : fitFig(el));
const ro = new ResizeObserver((es) => es.forEach((e) => fitEl(e.target)));
const observed = new WeakSet();
export function fitAll(root = document) {
    for (const el of $$(".heat, .figfit", root)) {
        fitEl(el);
        if (!observed.has(el)) {
            ro.observe(el);
            observed.add(el);
        }
    }
}
// Lists inside sheets show what fits and say how many are hidden.
export function fitList(ul, more, label) {
    if (!ul || !more)
        return;
    const items = Array.from(ul.children);
    items.forEach((li) => { li.hidden = false; });
    more.hidden = false;
    more.textContent = label(2);
    const box = ul.getBoundingClientRect();
    let hidden = 0;
    for (const li of items)
        if (li.getBoundingClientRect().bottom > box.bottom + 0.5) {
            li.hidden = true;
            hidden++;
        }
    more.hidden = !hidden;
    if (hidden)
        more.textContent = label(hidden);
}
const SHEETS = {};
const ACTS = {};
export const defineSheets = (s) => { Object.assign(SHEETS, s); };
export const defineActions = (a) => { Object.assign(ACTS, a); };
let cur = null;
let lastFocus = null;
let onClose = null;
export const sheetOpen = () => (cur ? cur.name : null);
export const sheetArg = () => cur?.arg;
export const setSheetArg = (arg) => { if (cur)
    cur.arg = arg; };
export const onSheetClose = (fn) => { onClose = fn; };
export function openSheet(name, arg) {
    const sheet = $("#ux-sheet"), scrim = $("#ux-scrim");
    if (!SHEETS[name] || !sheet || !scrim)
        return;
    if (!cur)
        lastFocus = document.activeElement;
    if (cur && cur.name !== name && onClose) {
        onClose();
        onClose = null;
    }
    cur = { name, arg };
    drawSheet();
    sheet.hidden = false;
    scrim.hidden = false;
    requestAnimationFrame(() => {
        sheet.classList.add("show");
        scrim.classList.add("show");
        fitAll(sheet);
    });
    // Focus the dialog itself: Tab then reaches its controls, and no button lights up on open.
    setTimeout(() => { if (!sheet.contains(document.activeElement))
        sheet.focus({ preventScroll: true }); }, 60);
}
export function drawSheet() {
    const sheet = $("#ux-sheet");
    if (!cur || !sheet)
        return;
    const active = document.activeElement;
    const keepId = active && sheet.contains(active) && active.tagName === "INPUT" ? active.id : null;
    const o = SHEETS[cur.name](cur.arg);
    sheet.className = `ux-sheet ${sheet.classList.contains("show") ? "show" : ""} ${o.tall ? "tall" : ""} ${o.wide ? "wide" : ""} ${o.dayw ? "dayw" : ""}`;
    sheet.style.setProperty("--c", o.c);
    sheet.innerHTML = o.html;
    if (keepId) {
        const i = document.getElementById(keepId);
        if (i) {
            i.focus({ preventScroll: true });
            i.setSelectionRange(i.value.length, i.value.length);
        }
    }
    fitAll(sheet);
    o.after?.();
}
export function closeSheet() {
    const sheet = $("#ux-sheet"), scrim = $("#ux-scrim");
    if (!sheet || !scrim || sheet.hidden)
        return;
    if (onClose) {
        onClose();
        onClose = null;
    }
    cur = null;
    sheet.classList.remove("show");
    scrim.classList.remove("show");
    setTimeout(() => {
        if (!sheet.classList.contains("show")) {
            sheet.hidden = true;
            scrim.hidden = true;
            sheet.innerHTML = "";
        }
    }, 300);
    if (lastFocus && document.contains(lastFocus))
        lastFocus.focus({ preventScroll: true });
    lastFocus = null;
}
export const head = (title, sub = "") => `<div class="ux-grab" aria-hidden="true"></div><header class="sh-h"><div class="sh-tt"><h3 id="ux-sheet-title">${title}</h3>${sub ? `<p class="sh-sub">${sub}</p>` : ""}</div><button type="button" class="ib" data-close aria-label="${esc(t("aria.close"))}">${I("close")}</button></header>`;
export const doneFoot = () => `<footer class="sh-f"><button type="button" class="btn ghost" data-close>${t("common.done")}</button></footer>`;
export const saveFoot = (act) => `<footer class="sh-f"><button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn" data-act="${act}">${t("common.save")}</button></footer>`;
let tipIndex = 0;
export function tipCard(tips) {
    if (!tips.length)
        return "";
    const i = tipIndex % tips.length, r = tips[i];
    const target = r.href ? `href="${esc(r.href)}"` : r.act ? `data-act="${r.act}"` : `data-open="${r.open}" ${r.arg ? `data-arg="${esc(r.arg)}"` : ""}`;
    const tag = r.href ? "a" : "button";
    return `<section class="w rec" style="--c:${r.c}" aria-label="${esc(t("tips.label"))}"><div class="rec-in">
      <${tag} ${tag === "button" ? 'type="button"' : ""} class="rec-main" ${target}>
        <span class="rec-top"><span class="ico">${I(r.icon)}</span><span class="rec-k">${t("tips.label")}</span></span>
        <span class="rec-t">${r.t}</span><span class="rec-d">${r.d}</span><span class="rec-cta">${r.cta}${I("next")}</span>
        <span class="rec-go">${I("next")}</span>
      </${tag}>
      ${tips.length > 1 ? `<button type="button" class="rec-next" data-act="tip" aria-label="${esc(t("aria.nextTip"))}"><span class="rn-l">${t("tips.next")}</span><span>${i + 1}/${tips.length}</span>${I("next")}</button>` : ""}
    </div></section>`;
}
export function heatCard(h) {
    const m0 = new Date(TODAY.getFullYear(), TODAY.getMonth() + h.off, 1);
    const days = new Date(m0.getFullYear(), m0.getMonth() + 1, 0).getDate();
    const lead = (m0.getDay() + 6) % 7, weeks = Math.ceil((lead + days) / 7);
    const w1 = get("wd1"), w2 = get("wd2");
    let cells = Array.from({ length: 7 }, (_, i) => `<span class="wd" aria-hidden="true"><span class="w1">${Array.isArray(w1) ? w1[i] : ""}</span><span class="w2">${Array.isArray(w2) ? w2[i] : ""}</span></span>`).join("");
    cells += Array.from({ length: lead }, () => `<span class="d blank"></span>`).join("");
    for (let i = 1; i <= days; i++) {
        const d = new Date(m0.getFullYear(), m0.getMonth(), i), k = key(d);
        cells += k > TK
            ? `<span class="d fut">${i}</span>`
            : `<button type="button" class="d ${k === TK ? "today" : ""}" data-l="${h.level(k)}" data-open="day" data-arg="${k}" aria-label="${esc(dayShort(d))}">${i}</button>`;
    }
    return `<section class="w heat" style="--c:${h.color}">
      <div class="ht-h"><b>${monthName(m0)}<small>${h.label}</small></b>
        <button type="button" class="ib sm" data-act="mon" data-mod="${h.mod}" data-d="-1" aria-label="${esc(t("aria.prevMonth"))}" ${h.off <= h.minOff ? "disabled" : ""}>${I("prev")}</button>
        <button type="button" class="ib sm" data-act="mon" data-mod="${h.mod}" data-d="1" aria-label="${esc(t("aria.nextMonth"))}" ${h.off >= 0 ? "disabled" : ""}>${I("next")}</button></div>
      <div class="ht-b">
        <div class="mgrid" data-weeks="${weeks}"><div class="mg">${cells}</div></div>
        <div class="ht-s">${h.stats.map(([v, l], i) => `<div class="hs ${i ? "" : "c"}"><b>${v}</b><span>${l}</span></div>`).join("")}
          <div class="ht-lg" aria-hidden="true"><span>${h.legend[0]}</span>${[1, 2, 3, 4].map((l) => `<i data-l="${l}"></i>`).join("")}<span>${h.legend[1]}</span></div></div>
      </div>
    </section>`;
}
export const monthKeys = (off) => {
    const m0 = new Date(TODAY.getFullYear(), TODAY.getMonth() + off, 1);
    const days = new Date(m0.getFullYear(), m0.getMonth() + 1, 0).getDate();
    return Array.from({ length: days }, (_, i) => key(new Date(m0.getFullYear(), m0.getMonth(), i + 1))).filter((k) => k <= TK);
};
export const monthsBack = (firstKey) => {
    if (!firstKey)
        return 0;
    const f = parse(firstKey);
    return Math.min(0, (f.getFullYear() - TODAY.getFullYear()) * 12 + f.getMonth() - TODAY.getMonth());
};
let renderPage = null;
export function render() {
    const main = $("#ux-main");
    if (!main || !renderPage)
        return;
    const p = renderPage();
    main.className = "ux-main " + p.cls;
    main.innerHTML = p.html;
    fitAll(main);
}
export const refresh = () => {
    render();
    if (cur)
        drawSheet();
};
export function mount(renderFn) {
    renderPage = renderFn;
    setFormat();
    render();
    addEventListener("resize", () => {
        if (setFormat())
            refresh();
        else
            fitAll();
    });
}
defineActions({
    tip(el) {
        tipIndex++;
        render();
        if (el)
            $(".rec-next")?.focus({ preventScroll: true });
    },
});
document.addEventListener("click", (e) => {
    const target = e.target;
    const a = target.closest("[data-act]");
    if (a && !a.disabled && ACTS[a.dataset.act || ""]) {
        ACTS[a.dataset.act || ""](a, e);
        return;
    }
    if (target.closest("[data-close]") || target.id === "ux-scrim") {
        closeSheet();
        return;
    }
    const o = target.closest("[data-open]");
    if (o && !o.disabled)
        openSheet(o.dataset.open || "", o.dataset.arg);
});
document.addEventListener("keydown", (e) => {
    const target = e.target;
    if (e.key === "Escape" && cur) {
        closeSheet();
        return;
    }
    if (e.key === "Tab" && cur) {
        // keep Tab inside the open sheet
        const sheet = $("#ux-sheet");
        const els = sheet ? [...sheet.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex='-1'])")].filter((el) => el.offsetParent !== null) : [];
        if (!sheet || !els.length)
            return;
        const first = els[0], last = els[els.length - 1];
        if (e.shiftKey && (document.activeElement === first || document.activeElement === sheet)) {
            e.preventDefault();
            last.focus();
        }
        else if (!e.shiftKey && (document.activeElement === last || !sheet.contains(document.activeElement))) {
            e.preventDefault();
            first.focus();
        }
        return;
    }
    if ((e.key === "Enter" || e.key === " ") && target.matches('[role="button"]:not(button)')) {
        e.preventDefault();
        target.click();
    }
});
