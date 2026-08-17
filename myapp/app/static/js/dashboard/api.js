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

export async function fetchRecommendations() {
    try {
        const res = await fetch("/api/recovery/recommendations");
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

export async function fetchRecentSessions(limit = 6) {
    try {
        const res = await fetch(`/api/training/sessions?limit=${encodeURIComponent(limit)}`);
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}
