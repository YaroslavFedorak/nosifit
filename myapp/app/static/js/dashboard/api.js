export async function fetchOverview() {
    try {
        const res = await fetch("/api/dashboard/today");
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

export async function fetchHeatmap() {
    try {
        const res = await fetch("/api/dashboard/heatmap");
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

export async function fetchRecommendation() {
    try {
        const res = await fetch("/api/dashboard/recommendation");
        if (!res.ok) return null;
        const json = await res.json();
        return json && Object.prototype.hasOwnProperty.call(json, "recommendation")
            ? json.recommendation
            : null;
    } catch {
        return null;
    }
}
