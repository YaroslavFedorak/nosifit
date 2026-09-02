export function renderRecommendations(container, recommendations) {
    if (!container) return;
    container.innerHTML = "";
    if (!recommendations) {
        const empty = document.createElement("div");
        empty.className = "db-recommendation-empty";
        empty.textContent = "Немає рекомендацій";
        container.appendChild(empty);
        return;
    }
    const list = document.createElement("div");
    list.className = "db-recommendation-list";
    const items = Array.isArray(recommendations) ? recommendations : [recommendations];
    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "db-recommendation-item";
        const title = document.createElement("div");
        title.className = "db-recommendation-title";
        title.textContent = item.title || item.name || (item.recommendation || "Рекомендація");
        const meta = document.createElement("div");
        meta.className = "db-recommendation-meta";
        meta.textContent = item.description || item.summary || "";
        row.appendChild(title);
        row.appendChild(meta);
        list.appendChild(row);
    });
    container.appendChild(list);
}
