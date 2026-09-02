const BASE = "/api/training";

async function jsonFetch(url, options = {}) {
    const r = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    let data = {};
    try {
        data = await r.json();
    } catch (_) {
        data = {};
    }

    if (!r.ok) {
        throw new Error(data.message || `HTTP ${r.status}`);
    }

    return data;
}

export const TrainingAPI = {
    getExercises(params = {}) {
        const q = new URLSearchParams(params).toString();
        const url = q ? `${BASE}/exercises?${q}` : `${BASE}/exercises`;
        return jsonFetch(url);
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
