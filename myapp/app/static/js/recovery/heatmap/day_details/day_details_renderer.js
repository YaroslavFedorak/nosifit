import { createMiniCard } from "./day_card.js";

export function renderDayDetails(bodyEl, data) {
    if (!data || !data.has_data) {
        bodyEl.innerHTML = `
            <div class="rc-list-block">
                <div class="rc-list-title">Немає даних</div>
                <div class="rc-list-item">За цей день немає записів.</div>
            </div>
        `;
        return;
    }

    const r = data.recovery;
    const s = data.sleep;
    const t = data.training;
    const h = data.habits;
    const rec = data.recommendations;

    // GRID
    const grid = document.createElement("div");
    grid.className = "rc-day-details-grid";

    grid.appendChild(createMiniCard("Відновлення", r.score ?? "—", r.status ?? "—", r.score ?? 0));
    grid.appendChild(createMiniCard("Сон", s.duration_minutes ?? "—", s.quality ?? "—", s.quality_score ?? 0));
    grid.appendChild(createMiniCard("Тренування", t.load ?? "—", t.sessions ?? "—", t.load ?? 0));
    grid.appendChild(createMiniCard("Звички", `${h.completed ?? 0}/${h.total ?? 0}`, h.score ?? "—", h.score ?? 0));

    bodyEl.appendChild(grid);

    // LISTS
    bodyEl.appendChild(block("Тренування", t.exercises?.length ? t.exercises.join(", ") : "Немає записів"));
    bodyEl.appendChild(block("Звички", h.items?.length ? h.items.map(x => x.name).join(", ") : "Немає записів"));
    bodyEl.appendChild(block("Рекомендації",
        rec.items?.length
            ? rec.items.map(r => r.text).join("<br>")
            : "Немає рекомендацій"
    ));
}

function block(title, content) {
    const el = document.createElement("div");
    el.className = "rc-list-block";
    el.innerHTML = `
        <div class="rc-list-title">${title}</div>
        <div class="rc-list-item">${content}</div>
    `;
    return el;
}
