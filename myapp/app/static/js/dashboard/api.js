export async function fetchOverview() {
    try {
        const response = await fetch("/api/dashboard/today");

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch {
        return null;
    }
}

export async function fetchHeatmap() {
    try {
        const response = await fetch("/api/dashboard/heatmap");

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch {
        return null;
    }
}

export async function fetchRecommendation() {
    try {
        const response = await fetch("/api/dashboard/recommendation");

        if (!response.ok) {
            return null;
        }

        const data = await response.json();

        return data?.recommendation ?? null;
    } catch {
        return null;
    }
}

export async function fetchTraining() {
    try {
        const response = await fetch("/api/dashboard/training");

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch {
        return null;
    }
}