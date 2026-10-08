const BASE = "/api/training";
async function jsonFetch(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });
    let data = {};
    try {
        data = await response.json();
    }
    catch {
        data = {};
    }
    if (!response.ok) {
        const message = typeof data === "object" &&
            data !== null &&
            "message" in data &&
            typeof data.message === "string"
            ? data.message
            : `HTTP ${response.status}`;
        throw new Error(message);
    }
    return data;
}
// The API caps page size, so a call without an explicit page walks every
// page and returns the whole catalog.
const EXERCISES_PAGE_SIZE = 100;
const EXERCISES_MAX_PAGES = 20;
export const TrainingAPI = {
    async getExercises(params = {}) {
        const buildUrl = (values) => {
            const query = new URLSearchParams(Object.entries(values).map(([key, value]) => [key, String(value)])).toString();
            return query
                ? `${BASE}/exercises?${query}`
                : `${BASE}/exercises`;
        };
        if ("page" in params) {
            return jsonFetch(buildUrl(params));
        }
        const items = [];
        for (let page = 1; page <= EXERCISES_MAX_PAGES; page += 1) {
            const data = await jsonFetch(buildUrl({
                ...params,
                page,
                per_page: EXERCISES_PAGE_SIZE
            }));
            const pageItems = data.items ?? [];
            items.push(...pageItems);
            if (pageItems.length < EXERCISES_PAGE_SIZE ||
                items.length >= (data.total ?? 0)) {
                break;
            }
        }
        return { items };
    },
    getPlans() {
        return jsonFetch(`${BASE}/plans`);
    },
    savePlan(payload) {
        return jsonFetch(`${BASE}/plans`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    updatePlan(id, payload) {
        return jsonFetch(`${BASE}/plans/${id}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
    },
    deletePlan(id) {
        return jsonFetch(`${BASE}/plans/${id}`, {
            method: "DELETE"
        });
    },
    completeSession(payload) {
        return jsonFetch(`${BASE}/sessions/complete`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    startSession(payload) {
        return jsonFetch(`${BASE}/sessions/start`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    finishSession(sessionId, payload) {
        return jsonFetch(`${BASE}/sessions/${sessionId}/finish`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    updateSessionExercise(sessionId, exerciseId, payload) {
        return jsonFetch(`${BASE}/sessions/${sessionId}/exercise/${exerciseId}`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    getAnalytics() {
        return jsonFetch(`${BASE}/analytics`);
    },
    getRecommendations() {
        return jsonFetch(`${BASE}/recommendations`);
    },
    getHeatmap(year = new Date().getFullYear()) {
        return jsonFetch(`${BASE}/heatmap?year=${year}`);
    },
    strengthTest(payload) {
        return jsonFetch(`${BASE}/strength-test`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },
    getToday() {
        return jsonFetch(`${BASE}/today`);
    },
    getTodaySession() {
        return jsonFetch(`${BASE}/today-session`);
    },
    getDayDetails(date) {
        return jsonFetch(`${BASE}/day/${date}`);
    }
};
