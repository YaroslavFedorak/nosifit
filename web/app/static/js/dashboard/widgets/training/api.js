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

export const trainingAPI = {
    getExercises(params = {}) {
        const q = new URLSearchParams(params).toString();
        const url = q ? `${BASE}/exercises?${q}` : `${BASE}/exercises`;
        return jsonFetch(url);
    },

    startTrainingSession(payload) {
        return jsonFetch(`${BASE}/sessions/start`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    addExerciseToSession(sessionId, exerciseId) {
        return jsonFetch(`${BASE}/sessions/${sessionId}/exercise/${exerciseId}`, {
            method: "POST",
            body: JSON.stringify({ exercise_id: exerciseId })
        });
    },

    updateSessionExercise(sessionId, exerciseId, payload) {
        return jsonFetch(`${BASE}/sessions/${sessionId}/exercise/${exerciseId}`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    },

    finishTrainingSession(sessionId, payload) {
        return jsonFetch(`${BASE}/sessions/${sessionId}/finish`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    }
};
