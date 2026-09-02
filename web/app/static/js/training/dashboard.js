export function renderCurrentDate() {
    const el = document.getElementById("current-date");
    if (!el) return;
    const d = new Date();
    el.textContent = d.toLocaleDateString("uk-UA", {
        weekday: "long",
        day: "numeric",
        month: "long"
    });
}

export function renderAnalytics(data) {
    const perf = data.performance || {};
    const rec = data.recovery || {};

    const perfEl = document.getElementById("tr-performance");
    const recEl = document.getElementById("tr-recovery");

    if (perfEl) {
        const avgPerf =
            (perf.pushups || 0) +
            (perf.squats || 0) +
            (perf.situps || 0);
        perfEl.textContent = avgPerf ? Math.round(avgPerf / 3) : "—";
    }

    if (recEl) {
        const avgRec =
            (rec.sleep || 0) -
            (rec.stress || 0) -
            (rec.soreness || 0);
        recEl.textContent = avgRec ? Math.round(avgRec) : "—";
    }
}

export function renderStrengthTestResults(perf) {
    if (!perf) return;
    const p = document.getElementById("st-result-pushups");
    const s = document.getElementById("st-result-squats");
    const si = document.getElementById("st-result-situps");
    if (p) p.textContent = perf.pushups ?? "—";
    if (s) s.textContent = perf.squats ?? "—";
    if (si) si.textContent = perf.situps ?? "—";
}
