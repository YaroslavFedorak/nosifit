/* Landing page behaviour: reveal on scroll, the module index, the sample
   water widget and the year heatmap. Everything here is sample data and
   nothing is saved; the page stays readable without this script. */

type Metric = "balance" | "training" | "recovery" | "nutrition";

interface SampleDay {
    date: Date;
    levels: Record<Metric, number>;
}

const DAY_MS = 86_400_000;
const WEEKS = 53;

// The sample year ends on the same fixed day as the hero panel, never on
// the visitor's own date: nothing here should read as their data.
const SAMPLE_END = new Date(2026, 9, 9);

const locale =
    document.documentElement.lang || undefined;

const reducedMotion =
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function startOfDay(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/* ---------- Reveal on scroll ---------- */

function initReveal(root: HTMLElement): void {
    if (reducedMotion || !("IntersectionObserver" in window)) {
        return;
    }

    const items =
        Array.from(root.querySelectorAll<HTMLElement>("[data-reveal]"));

    // Whatever is already on screen stays visible: no flash on load.
    for (const item of items) {
        if (item.getBoundingClientRect().top < window.innerHeight) {
            item.classList.add("is-visible");
        }
    }

    root.classList.add("is-motion");

    const observer =
        new IntersectionObserver(
            entries => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                }
            },
            { rootMargin: "0px 0px -12% 0px" }
        );

    for (const item of items) {
        if (!item.classList.contains("is-visible")) {
            observer.observe(item);
        }
    }
}

/* ---------- Module index ---------- */

function initIndex(): void {
    const links =
        Array.from(document.querySelectorAll<HTMLAnchorElement>("[data-index-link]"));

    const chapters =
        Array.from(document.querySelectorAll<HTMLElement>("[data-chapter]"));

    if (!links.length || !chapters.length || !("IntersectionObserver" in window)) {
        return;
    }

    const setActive = (key: string): void => {
        for (const link of links) {
            const active = link.dataset.indexLink === key;

            link.classList.toggle("is-active", active);

            if (active) {
                link.setAttribute("aria-current", "true");
            } else {
                link.removeAttribute("aria-current");
            }
        }
    };

    const observer =
        new IntersectionObserver(
            entries => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        setActive((entry.target as HTMLElement).dataset.chapter ?? "");
                    }
                }
            },
            { rootMargin: "-40% 0px -55% 0px" }
        );

    chapters.forEach(chapter => observer.observe(chapter));
}

/* ---------- Sample water widget ---------- */

function initWater(): void {
    const widget =
        document.querySelector<HTMLElement>("[data-water]");

    if (!widget) {
        return;
    }

    const button =
        widget.querySelector<HTMLButtonElement>("[data-water-add]");

    const value =
        widget.querySelector<HTMLElement>("[data-water-value]");

    const cells =
        Array.from(widget.querySelectorAll<HTMLElement>(".lp-water-cells i"));

    if (!button || !value) {
        return;
    }

    const goal = Number(widget.dataset.goal);
    const step = Number(widget.dataset.step);
    let current = Number(widget.dataset.current);

    const format =
        new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });

    // The text is "<current> / <goal> <unit>"; only the first number changes.
    const template = value.textContent?.trim() ?? "";
    const rest = template.slice(template.indexOf("/"));

    const render = (): void => {
        const filled = Math.round((current / goal) * cells.length);

        cells.forEach((cell, index) => cell.classList.toggle("is-on", index < filled));
        value.textContent = `${format.format(current)} ${rest}`;
        button.disabled = current >= goal;
    };

    button.addEventListener("click", () => {
        current = Math.min(goal, Math.round((current + step) * 100) / 100);
        render();
    });
}

/* ---------- Year heatmap ---------- */

// Deterministic sample data: the same picture on every visit.
function random(seed: number): () => number {
    let state = seed >>> 0;

    return () => {
        state = (state + 0x6d2b79f5) >>> 0;
        let t = state;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

function buildYear(end: Date): { start: Date; days: SampleDay[] } {
    const mondayOffset = (end.getDay() + 6) % 7;
    const start = new Date(end.getTime() - (mondayOffset + (WEEKS - 1) * 7) * DAY_MS);
    const next = random(20261009);

    const days: SampleDay[] = [];
    let previousLoad = 0;

    for (let index = 0; index < WEEKS * 7; index += 1) {
        const date = startOfDay(new Date(start.getTime() + index * DAY_MS + DAY_MS / 2));
        const weekday = index % 7;
        const logged = index >= 35 && next() > 0.06;

        // Later weeks are more regular: the habit of logging settles in.
        const regularity = clamp(index / (WEEKS * 7), 0.35, 1);
        const plannedDay = weekday === 0 || weekday === 2 || weekday === 4 || (weekday === 5 && next() < 0.45);
        const trained = logged && plannedDay && next() < 0.7 + regularity * 0.25;

        let load = 0;

        if (trained) {
            // Mostly moderate sessions; a hard day now and then.
            load = 2 + Math.floor(next() * 2);

            const roll = next();

            if (roll < 0.06) {
                load += 3;
            } else if (roll < 0.3) {
                load += 1;
            }
        }

        const sleep = next();
        const recovery = logged
            ? clamp(Math.round(1.6 + sleep * 3 - (previousLoad >= 5 ? 2 : previousLoad >= 4 ? 1 : 0)), 1, 5)
            : 0;
        const nutrition = logged && next() > 0.12
            ? clamp(Math.round(1 + next() * 2 + regularity), 1, 4)
            : 0;

        const present = [load, recovery, nutrition].filter(level => level > 0);
        const balance = present.length
            ? clamp(Math.round(present.reduce((sum, level) => sum + level, 0) / present.length), 1, 5)
            : 0;

        days.push({
            date,
            levels: {
                balance,
                training: clamp(load, 0, 6),
                recovery,
                nutrition
            }
        });

        previousLoad = load;
    }

    return { start, days };
}

function initHeatmap(): void {
    const root =
        document.querySelector<HTMLElement>("[data-heat]");

    const grid =
        root?.querySelector<HTMLElement>("[data-heat-grid]");

    const months =
        root?.querySelector<HTMLElement>("[data-heat-months]");

    const readout =
        root?.querySelector<HTMLElement>("[data-heat-readout]");

    const scroller =
        root?.querySelector<HTMLElement>("[data-heat-scroll]");

    if (!root || !grid || !months || !readout || !scroller) {
        return;
    }

    const buttons =
        Array.from(document.querySelectorAll<HTMLButtonElement>("[data-metric]"));

    const { days } = buildYear(SAMPLE_END);
    const lastIndex = days.findIndex(day => day.date.getTime() === SAMPLE_END.getTime());

    let metric: Metric = "balance";
    let active = -1;

    const dayFormat =
        new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short", year: "numeric" });

    const monthFormat =
        new Intl.DateTimeFormat(locale, { month: "short" });

    const cells: HTMLElement[] = days.map((_day, index) => {
        const cell = document.createElement("span");

        cell.className = "lp-heat-cell";
        cell.dataset.index = String(index);
        cell.setAttribute("aria-hidden", "true");

        if (index > lastIndex) {
            cell.classList.add("is-empty");
        }

        return cell;
    });

    grid.replaceChildren(...cells);

    // Month labels sit over the first week that contains the 1st.
    let lastLabel = -4;
    const labels: HTMLElement[] = [];

    for (let week = 0; week < WEEKS; week += 1) {
        const weekDays = days.slice(week * 7, week * 7 + 7);
        const first = weekDays.find(day => day.date.getDate() === 1);

        if ((first || week === 0) && week - lastLabel >= 4) {
            const label = document.createElement("span");

            label.textContent = monthFormat.format((first ?? weekDays[0]).date);
            label.style.gridColumn = `${week + 1}`;
            labels.push(label);
            lastLabel = week;
        }
    }

    months.replaceChildren(...labels);

    const label = (key: string): string => root.dataset[key] ?? "";

    const describe = (index: number): string => {
        const day = days[index];
        const level = day.levels[metric];
        const metricName = label(`label${metric[0].toUpperCase()}${metric.slice(1)}`);
        const value = level > 0
            ? label("labelLevel").replace("{level}", String(level))
            : label("labelNoData");

        return `${dayFormat.format(day.date)} · ${metricName}: ${value}`;
    };

    const paint = (): void => {
        days.forEach((day, index) => {
            cells[index].dataset.level = String(index > lastIndex ? 0 : day.levels[metric]);
        });

        if (active >= 0) {
            readout.textContent = describe(active);
        }
    };

    const select = (index: number): void => {
        const next = clamp(index, 0, lastIndex);

        if (active >= 0) {
            cells[active].classList.remove("is-active");
        }

        active = next;
        cells[active].classList.add("is-active");
        readout.textContent = describe(active);
    };

    grid.addEventListener("pointerover", event => {
        const cell = (event.target as HTMLElement).closest<HTMLElement>(".lp-heat-cell");

        if (cell && !cell.classList.contains("is-empty")) {
            select(Number(cell.dataset.index));
        }
    });

    grid.addEventListener("focus", () => {
        if (active < 0) {
            select(lastIndex);
        }
    });

    grid.addEventListener("keydown", event => {
        const moves: Record<string, number> = {
            ArrowLeft: -7,
            ArrowRight: 7,
            ArrowUp: -1,
            ArrowDown: 1
        };

        if (event.key in moves) {
            select((active < 0 ? lastIndex : active) + moves[event.key]);
        } else if (event.key === "Home") {
            select(days.findIndex(day => day.levels.balance > 0));
        } else if (event.key === "End") {
            select(lastIndex);
        } else {
            return;
        }

        event.preventDefault();
    });

    for (const button of buttons) {
        button.addEventListener("click", () => {
            metric = (button.dataset.metric as Metric) ?? "balance";

            for (const other of buttons) {
                other.setAttribute("aria-pressed", String(other === button));
            }

            paint();
        });
    }

    paint();
    select(lastIndex);

    // On narrow screens show the latest weeks first.
    scroller.scrollLeft = scroller.scrollWidth;
}

const root =
    document.querySelector<HTMLElement>(".lp");

if (root) {
    root.classList.add("is-js");
    initReveal(root);
    initIndex();
    initWater();
    initHeatmap();
}
