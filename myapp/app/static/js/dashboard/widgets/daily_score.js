export function renderDailyScore(root, data) {
    const t = data.training.score ?? 0;
    const n = data.nutrition.score ?? 0;
    const r = data.recovery.score ?? 0;
    root.innerHTML = `
        <div class="nf-daily-score">
            <div class="nf-daily-score-main">
                <div class="nf-daily-score-value">${data.daily_score}</div>
                <div class="nf-daily-score-label">Daily Score</div>
            </div>
            <div class="nf-daily-score-breakdown">
                <div class="nf-daily-score-item">
                    <div class="label">Training</div>
                    <div class="value">${t}</div>
                </div>
                <div class="nf-daily-score-item">
                    <div class="label">Nutrition</div>
                    <div class="value">${n}</div>
                </div>
                <div class="nf-daily-score-item">
                    <div class="label">Recovery</div>
                    <div class="value">${r}</div>
                </div>
            </div>
        </div>
    `;
}
