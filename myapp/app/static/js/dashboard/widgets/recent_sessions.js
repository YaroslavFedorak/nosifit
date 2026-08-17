import { el } from "../utils/dom.js";

export function renderRecentSessions(container, sessions) {
    container.innerHTML = "";
    if (!sessions || !Array.isArray(sessions) || sessions.length === 0) {
        container.textContent = "Немає сесій";
        return;
    }
    for (const s of sessions) {
        const title = s.title || s.name || "Сесія";
        const meta = s.started_at ? new Date(s.started_at).toLocaleString() : "";
        const node = el("div", { class: "dashboard-session-item" }, [
            el("div", { class: "dashboard-session-title", text: title }),
            el("div", { class: "dashboard-session-meta", text: meta })
        ]);
        container.appendChild(node);
    }
}
