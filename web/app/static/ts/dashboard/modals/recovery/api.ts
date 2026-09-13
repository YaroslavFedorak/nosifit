const API_BASE = "/api/recovery";

const DEFAULT_TIMEOUT_MS = 10000;

async function request(
    url: string,
    options: RequestInit = {},
    timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<any> {
    const controller =
        new AbortController();

    const timeoutId =
        window.setTimeout(
            () => controller.abort(),
            timeoutMs
        );

    try {
        const response =
            await fetch(url, {
                headers: {
                    "Content-Type":
                        "application/json",
                    ...(options.headers || {})
                },
                signal:
                    controller.signal,
                ...options
            });

        if (!response.ok) {
            let message =
                `HTTP ${response.status}`;

            try {
                const contentType =
                    response.headers.get(
                        "content-type"
                    ) || "";

                if (
                    contentType.includes(
                        "application/json"
                    )
                ) {
                    const error =
                        await response.json();

                    if (
                        error &&
                        error.error
                    ) {
                        message =
                            error.error;
                    }
                } else {
                    const text =
                        await response.text();

                    if (text) {
                        message = text;
                    }
                }
            } catch (_) {}

            throw new Error(message);
        }

        const contentType =
            response.headers.get(
                "content-type"
            ) || "";

        if (
            contentType.includes(
                "application/json"
            )
        ) {
            return await response.json();
        }

        return null;
    } catch (error: any) {
        if (
            error &&
            error.name === "AbortError"
        ) {
            throw new Error(
                "Request timeout"
            );
        }

        throw error;
    } finally {
        window.clearTimeout(
            timeoutId
        );
    }
}

const ENDPOINTS = {
    snapshot: (
        userId: string | number,
        date?: string | null
    ): string =>
        date
            ? `${API_BASE}/snapshot/${userId}?date=${encodeURIComponent(date)}`
            : `${API_BASE}/snapshot/${userId}`,

    heatmap: (
        userId: string | number,
        year: number
    ): string =>
        `${API_BASE}/heatmap/${userId}?year=${year}`,

    recommendations: (
        userId: string | number
    ): string =>
        `${API_BASE}/recommendations/${userId}`,

    sleep: (): string =>
        `${API_BASE}/sleep`,

    addHabit: (
        habitId: string | number
    ): string =>
        `${API_BASE}/habits/add/${habitId}`,

    removeHabit: (
        userHabitId: string | number
    ): string =>
        `${API_BASE}/habits/${userHabitId}`,

    logHabit: (): string =>
        `${API_BASE}/habits/logs`,

    habitsList: (): string =>
        `${API_BASE}/habits/list`,

    userHabits: (
        userId: string | number
    ): string =>
        `${API_BASE}/habits/user/${userId}`,

    dayDetails: (
        userId: string | number,
        date: string
    ): string =>
        `${API_BASE}/day-details/${userId}?date=${encodeURIComponent(date)}`
};

export const RecoveryAPI = {
    getSnapshot(
        userId: string | number,
        date: string | null = null
    ): Promise<any> {
        return request(
            ENDPOINTS.snapshot(
                userId,
                date
            )
        );
    },

    getHeatmap(
        userId: string | number,
        year: number
    ): Promise<any> {
        return request(
            ENDPOINTS.heatmap(
                userId,
                year
            )
        );
    },

    getRecommendations(
        userId: string | number
    ): Promise<any> {
        return request(
            ENDPOINTS.recommendations(
                userId
            )
        );
    },

    addSleep(
        userId: string | number,
        sleepStart: string,
        sleepEnd: string
    ): Promise<any> {
        return request(
            ENDPOINTS.sleep(),
            {
                method: "POST",
                body: JSON.stringify({
                    user_id: userId,
                    sleep_start:
                        sleepStart,
                    sleep_end:
                        sleepEnd
                })
            }
        );
    },

    addHabit(
        userId: string | number,
        habitId: string | number
    ): Promise<any> {
        return request(
            ENDPOINTS.addHabit(
                habitId
            ),
            {
                method: "POST",
                body: JSON.stringify({
                    user_id: userId
                })
            }
        );
    },

    removeHabit(
        userHabitId: string | number
    ): Promise<any> {
        return request(
            ENDPOINTS.removeHabit(
                userHabitId
            ),
            {
                method: "DELETE"
            }
        );
    },

    logHabit(
        userHabitId: string | number
    ): Promise<any> {
        return request(
            ENDPOINTS.logHabit(),
            {
                method: "POST",
                body: JSON.stringify({
                    user_habit_id:
                        userHabitId
                })
            }
        );
    },

    getHabitsList(): Promise<any> {
        return request(
            ENDPOINTS.habitsList()
        );
    },

    getUserHabits(
        userId: string | number
    ): Promise<any> {
        return request(
            ENDPOINTS.userHabits(
                userId
            )
        );
    },

    getDayDetails(
        userId: string | number,
        date: string
    ): Promise<any> {
        return request(
            ENDPOINTS.dayDetails(
                userId,
                date
            )
        );
    }
};