const BASE = "/api/training";

async function jsonFetch(
    url: string,
    options: RequestInit = {}
): Promise<any> {
    const response = await fetch(url, {
        headers: {
            "Content-Type":
                "application/json"
        },
        ...options
    });

    let data: any = {};

    try {
        data =
            await response.json();
    } catch (_) {
        data = {};
    }

    if (!response.ok) {
        throw new Error(
            data?.message ||
            `HTTP ${response.status}`
        );
    }

    return data;
}

export const trainingAPI = {
    getExercises(
        params: Record<string, string> = {}
    ): Promise<any> {
        const q =
            new URLSearchParams(
                params
            ).toString();

        const url = q
            ? `${BASE}/exercises?${q}`
            : `${BASE}/exercises`;

        return jsonFetch(url);
    },

    getPlans(): Promise<any[]> {
        return jsonFetch(
            `${BASE}/plans`
        );
    },

    savePlan(
        payload: any
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/plans`,
            {
                method: "POST",
                body: JSON.stringify(
                    payload
                )
            }
        );
    },

    updatePlan(
        id: string | number,
        payload: any
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/plans/${id}`,
            {
                method: "PUT",
                body: JSON.stringify(
                    payload
                )
            }
        );
    },

    startTrainingSession(
        payload: any
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/sessions/start`,
            {
                method: "POST",
                body: JSON.stringify(
                    payload
                )
            }
        );
    },

    addExerciseToSession(
        sessionId: string,
        exerciseId: string
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/sessions/${sessionId}/exercise/${exerciseId}`,
            {
                method: "POST",
                body: JSON.stringify({
                    exercise_id:
                        exerciseId
                })
            }
        );
    },

    updateSessionExercise(
        sessionId: string,
        exerciseId: string,
        payload: any
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/sessions/${sessionId}/exercise/${exerciseId}`,
            {
                method: "POST",
                body: JSON.stringify(
                    payload
                )
            }
        );
    },

    finishTrainingSession(
        sessionId: string,
        payload: any
    ): Promise<any> {
        return jsonFetch(
            `${BASE}/sessions/${sessionId}/finish`,
            {
                method: "POST",
                body: JSON.stringify(
                    payload
                )
            }
        );
    }
};

export const TrainingAPI =
    trainingAPI;