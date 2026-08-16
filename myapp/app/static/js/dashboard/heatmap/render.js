export function renderHeatmap(root, days) {
    const cells = days.map(d => {
        const level = scoreLevel(d.daily_score);
        return `<div class="nf-heatmap-day" data-date="${d.date}" data-score="${d.daily_score}" data-level="${level}">
            <span class="nf-heatmap-day-number">${new Date(d.date).getDate()}</span>
        </div>`;
    }).join("");
    root.innerHTML = `<div class="nf-heatmap-grid">${cells}</div>`;
    root.querySelectorAll(".nf-heatmap-day").forEach(el => {
        el.addEventListener("click", () => {
            const date = el.dataset.date;
            const evt = new CustomEvent("dashboard:dayclick", { detail: { date } });
            window.dispatchEvent(evt);
        });
        el.addEventListener("mouseenter", (ev) => {
            const date = el.dataset.date;
            const score = el.dataset.score;
            const evt = new CustomEvent("dashboard:dayhover", { detail: { date, score, target: el } });
            window.dispatchEvent(evt);
        });
        el.addEventListener("mouseleave", () => {
            const evt = new CustomEvent("dashboard:dayhoverout");
            window.dispatchEvent(evt);
        });
    });
    function scoreLevel(s) {
        const v = Number(s) || 0;
        if (v >= 80) return "high";
        if (v >= 60) return "medium";
        if (v >= 40) return "low";
        return "none";
    }
}
