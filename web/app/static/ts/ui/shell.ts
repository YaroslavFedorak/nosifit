// App shell on every signed-in page: keeps the layout format current and fills the streak chip.

const STREAK_KEY = "nf-streak";

const setFormat = (): void => {
    const w = innerWidth, h = innerHeight, land = w > h, r = document.documentElement;
    r.classList.remove("f-p", "f-s", "f-t", "f-l", "f-d");
    if (!land) r.classList.add(w >= 600 ? "f-t" : "f-p", ...(w < 600 && h < 700 ? ["f-s"] : []));
    else r.classList.add(w >= 900 && h >= 521 ? "f-d" : "f-l");
};

interface HeatDay {
    date: string;
    nutrition?: { calories?: number };
    recovery?: { sleep_hours?: number };
    training?: { completed?: boolean };
}

// Days in a row, up to today, with anything logged; today may still be empty.
export const streakOf = (days: HeatDay[], today: string): number => {
    const active = new Set(
        days
            .filter((d) => (d.nutrition?.calories || 0) > 0 || (d.recovery?.sleep_hours || 0) > 0 || d.training?.completed)
            .map((d) => d.date),
    );
    let n = 0;
    const d = new Date(today + "T12:00:00");
    if (!active.has(today)) d.setDate(d.getDate() - 1);
    for (;;) {
        const k = d.toISOString().slice(0, 10);
        if (!active.has(k)) break;
        n++;
        d.setDate(d.getDate() - 1);
    }
    return n;
};

export const showStreak = (n: number): void => {
    for (const chip of document.querySelectorAll<HTMLElement>("[data-streak]")) {
        const b = chip.querySelector("b");
        if (b) b.textContent = new Intl.NumberFormat(document.documentElement.lang || "en").format(n);
        chip.hidden = n < 1;
    }
};

async function loadStreak(): Promise<void> {
    const today = document.body.dataset.today || "";
    try {
        const cached = JSON.parse(sessionStorage.getItem(STREAK_KEY) || "null");
        if (cached && cached.today === today) {
            showStreak(cached.n);
            return;
        }
    } catch {
        // Storage can be blocked; fall through to the request.
    }
    try {
        const res = await fetch("/api/dashboard/heatmap", { credentials: "same-origin", headers: { Accept: "application/json" } });
        if (!res.ok) return;
        const data = await res.json();
        const n = streakOf(data.days || [], today);
        showStreak(n);
        try {
            sessionStorage.setItem(STREAK_KEY, JSON.stringify({ today, n }));
        } catch {
            // Not cached this time.
        }
    } catch {
        // No streak chip without the data.
    }
}

addEventListener("resize", setFormat);
void loadStreak();
