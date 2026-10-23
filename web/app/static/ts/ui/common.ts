// Sheets every tab shares: the details of a day picked on a heatmap or the week strip.

import {
    api, defineSheets, drawSheet, sheetOpen, sheetArg, head, doneFoot, t, tn, I, esc,
    parse, dayLong, TK, fmtN, U, dur, liters,
} from "./core.js";

interface DashDay {
    date: string;
    nutrition: { calories: number; protein: number; water: number };
    recovery: { sleep_hours: number };
    training: { completed: boolean; duration: number; exercise_count: number };
}

const days: Record<string, DashDay | "loading" | "error"> = {};

async function loadDay(k: string): Promise<void> {
    if (days[k] && days[k] !== "error") return;
    days[k] = "loading";
    try {
        days[k] = await api<DashDay>(`/api/dashboard/day/${k}`);
    } catch {
        days[k] = "error";
    }
    if (sheetOpen() === "day" && sheetArg() === k) drawSheet();
}

export function defineDaySheet(extraRows?: (k: string) => string): void {
    defineSheets({
        day(k?: string) {
            const date = k || TK;
            const d = days[date];
            if (!d) void loadDay(date);
            let body: string;
            if (!d || d === "loading") body = `<p class="fl-empty">${t("common.loading")}</p>`;
            else if (d === "error") body = `<p class="fl-empty">${t("err.load")}</p>`;
            else {
                const sleepMin = Math.round((d.recovery.sleep_hours || 0) * 60);
                const rows: [string, string, string, string | null, string][] = [
                    ["train", "var(--train)", t("tile.workout"),
                        d.training.completed ? tn("pl.ex", d.training.exercise_count) : null,
                        d.training.duration ? `${fmtN(d.training.duration)} ${U("min")}` : ""],
                    ["food", "var(--food)", t("tile.kcal"), d.nutrition.calories ? `${fmtN(d.nutrition.calories)} ${U("kcal")}` : null,
                        d.nutrition.protein ? `${t("mac.p")} ${fmtN(d.nutrition.protein)} ${U("g")}` : ""],
                    ["moon", "var(--sleep)", t("tile.sleep"), sleepMin ? dur(sleepMin) : null, ""],
                    ["drop", "var(--water)", t("tile.water"), d.nutrition.water ? liters(d.nutrition.water) : null, ""],
                ];
                body = `<ul class="dl">${rows
                    .map(([i, c, l, v, s]) => `<li class="${v ? "" : "off"}"><span class="ico" style="--c:${c}">${I(i)}</span><span class="dl-b"><b>${esc(l)}</b>${s ? `<span>${esc(s)}</span>` : ""}</span><span class="dl-v">${v ? esc(v) : "—"}</span></li>`)
                    .join("")}</ul>${extraRows ? extraRows(date) : ""}`;
            }
            return {
                c: "var(--rec)", dayw: true,
                html: head(dayLong(parse(date)), date === TK ? t("common.today") : "") + `<div class="sh-b">${body}</div>` + doneFoot(),
            };
        },
    });
}

// Opens the sheet named in the address (#sheet:name:arg), as the home tiles link to it.
export function openFromHash(open: (name: string, arg?: string) => void): void {
    const m = /^#sheet:([a-z]+)(?::([\w-]+))?$/.exec(location.hash);
    if (!m) return;
    history.replaceState(null, "", location.pathname + location.search);
    open(m[1], m[2]);
}
