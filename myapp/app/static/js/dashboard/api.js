async function request(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                Accept: "application/json",
                ...(options.headers || {})
            },
            cache: "no-store"
        });

        if (!response.ok) {
            const errorText = await response.text();

            console.error(
                `Dashboard API error: ${response.status} ${url}`,
                errorText
            );

            return null;
        }

        const contentType =
            response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error(
            `Dashboard API error: ${url}`,
            error
        );

        return null;
    }
}


export async function fetchOverview() {
    return request("/api/dashboard/today");
}


export async function fetchHeatmap() {
    return request("/api/dashboard/heatmap");
}


export async function fetchRecommendation() {
    const data =
        await request(
            "/api/dashboard/recommendation"
        );

    if (!data) {
        return null;
    }

    return data.recommendation ?? data;
}


export async function fetchTraining() {
    return request(
        "/api/dashboard/training"
    );
}


export async function fetchExercises() {
    return request(
        "/api/dashboard/training/exercises"
    );
}


export async function startTrainingSession(
    payload = {}
) {
    return request(
        "/api/dashboard/training/session",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(payload)
        }
    );
}


export async function addExerciseToSession(
    sessionId,
    exerciseId
) {
    if (
        sessionId == null ||
        exerciseId == null
    ) {
        return null;
    }

    return request(
        `/api/dashboard/training/session/${sessionId}/exercise`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify({
                exercise_id: exerciseId
            })
        }
    );
}


export async function updateSessionExercise(
    sessionId,
    exerciseId,
    payload = {}
) {
    if (
        sessionId == null ||
        exerciseId == null
    ) {
        return null;
    }

    const normalizedPayload = {
        ...payload
    };

    if (
        normalizedPayload.load_done === "" ||
        normalizedPayload.load_done == null
    ) {
        normalizedPayload.load_done = null;
    }

    if (
        normalizedPayload.sets_done === "" ||
        normalizedPayload.sets_done == null
    ) {
        normalizedPayload.sets_done = null;
    }

    if (
        normalizedPayload.reps_done === "" ||
        normalizedPayload.reps_done == null
    ) {
        normalizedPayload.reps_done = null;
    }

    if (
        normalizedPayload.rpe === "" ||
        normalizedPayload.rpe == null
    ) {
        normalizedPayload.rpe = null;
    }

    return request(
        `/api/dashboard/training/session/${sessionId}/exercise/${exerciseId}`,
        {
            method: "PATCH",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(
                normalizedPayload
            )
        }
    );
}


export async function finishTrainingSession(
    sessionId,
    payload = {}
) {
    if (sessionId == null) {
        return null;
    }

    return request(
        `/api/dashboard/training/session/${sessionId}/finish`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(payload)
        }
    );
}


export async function saveWorkout(
    payload
) {
    return request(
        "/api/dashboard/training",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(payload)
        }
    );
}