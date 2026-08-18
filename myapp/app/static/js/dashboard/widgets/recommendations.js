import { el } from "../utils/dom.js";

export function renderRecommendations(container, recommendation) {
    container.innerHTML = "";

    if (!recommendation || typeof recommendation !== "object") {
        container.textContent = "Немає рекомендацій";
        return;
    }

    const title = recommendation.title || "Без назви";
    const reason = recommendation.reason || recommendation.message || "";

    const node = el("div", { class: "dashboard-recommendation-item" }, [
        el("div", { class: "dashboard-recommendation-title", text: title }),
        el("div", { class: "dashboard-recommendation-reason", text: reason })
    ]);

    container.appendChild(node);
}
