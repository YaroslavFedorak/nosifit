export const DashboardAPI = {
    async today() {
        const r = await fetch("/api/dashboard/today", { credentials: "same-origin" });
        if (!r.ok) throw new Error("Failed to load dashboard today");
        return r.json();
    },
    async heatmap() {
        const r = await fetch("/api/dashboard/heatmap", { credentials: "same-origin" });
        if (!r.ok) throw new Error("Failed to load dashboard heatmap");
        return r.json();
    },
    async day(dateIso) {
        const r = await fetch(`/api/dashboard/day/${dateIso}`, { credentials: "same-origin" });
        if (!r.ok) throw new Error("Failed to load dashboard day");
        return r.json();
    }
};
