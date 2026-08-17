import { el } from "../utils/dom.js";

export function renderRecommendations(container, data) {
    container.innerHTML = "";
    if (!data || !data.recommendations || !Array.isArray(data.recommendations.items) || data.recommendations.items.length === 0) {
        container.textContent = "Немає рекомендацій";
        return;
    }
    const items = data.recommendations.items.slice(0, 3);
    for (const item of items) {
        const node = el("div", { class: "dashboard-recommendation-item" }, [
            el("div", { class: "dashboard-recommendation-title", text: item.title || "Без назви" }),
            el("div", { class: "dashboard-recommendation-reason", text: item.reason || item.message || "" })
        ]);
        container.appendChild(node);
    }
}
