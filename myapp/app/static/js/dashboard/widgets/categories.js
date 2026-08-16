export function renderCategories(root, data) {
    root.innerHTML = `
        <div class="nf-categories">
            <a class="nf-cat" href="/recovery">
                <div class="nf-cat-title">Recovery</div>
                <div class="nf-cat-score">${data.recovery.score ?? 0}</div>
                <div class="nf-cat-sub">Sleep ${data.recovery.sleep_hours ?? 0}h</div>
            </a>
            <a class="nf-cat" href="/nutrition">
                <div class="nf-cat-title">Nutrition</div>
                <div class="nf-cat-score">${data.nutrition.score ?? 0}</div>
                <div class="nf-cat-sub">Calories ${data.nutrition.calories ?? 0}</div>
            </a>
            <a class="nf-cat" href="/training">
                <div class="nf-cat-title">Training</div>
                <div class="nf-cat-score">${data.training.score ?? 0}</div>
                <div class="nf-cat-sub">Duration ${data.training.duration ?? 0} min</div>
            </a>
        </div>
    `;
}
