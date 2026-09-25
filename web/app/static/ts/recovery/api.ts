import {
    translate
} from "../i18n/loader.js";

export interface RecoverySnapshot {
    date: string;
    score: number | null;
    energy_score: number | null;
    sleep_score: number | null;
    training_score: number | null;
    nutrition_score: number | null;
    habits_score: number | null;
    status: string | null;
    recovery_score?: number | null;
    recovery_percent?: number | null;
    habits?: RecoveryHabit[];
}

export interface RecoveryHeatmapDay {
    date?: string | null;
    level?: number | null;
    recovery_score?: number | null;
    percent?: number | null;
    load?: number | null;
    is_today?: boolean;
}

export interface RecoveryHeatmapResponse {
    days?: RecoveryHeatmapDay[];
}

export interface RecoveryTrendPoint {
    date: string;
    score: number | null;
    energy_score: number | null;
    sleep_score: number | null;
    training_score: number | null;
    nutrition_score: number | null;
    habits_score: number | null;
}

export interface RecoveryHabit {
    id?: number | string;
    habit_id?: number | string;
    user_habit_id?: number | string;
    name?: string | null;
    description?: string | null;
    category?: string | null;
    icon?: string | null;
    slug?: string | null;
    points?: number | null;
    completed?: boolean;
}

export interface RecoveryRecommendation {
    id?: string | null;
    icon?: string | null;
    text?: string | null;
    title?: string | null;
    description?: string | null;
    message?: string | null;
    reason?: unknown;
    priority?: string | null;
    type?: string | null;
    muscle?: string | null;
}

export interface RecoveryRecommendationsResponse {
    recommendations:
        | RecoveryRecommendation[]
        | {
            items?: RecoveryRecommendation[];
        }
        | null;
}

export interface RecoveryTrainingExercise {
    name?: string | null;
    exercise_name?: string | null;
    sets?: number | null;
    reps?: number | null;
    weight?: number | null;
    volume?: number | null;
}

export interface RecoveryDayDetails {
    date: string;
    has_data: boolean;
    recovery: {
        score: number | null;
        status: string | null;
        energy_score: number | null;
    };
    sleep: {
        duration_minutes: number | null;
        quality_score: number | null;
        bedtime: string | null;
        wake_time: string | null;
    };
    training: {
        load: number | null;
        sessions: number;
        exercises: RecoveryTrainingExercise[];
    };
    habits: {
        completed: number;
        total: number;
        score: number | null;
        items: RecoveryHabit[];
    };
    recommendations: {
        total: number;
        items: RecoveryRecommendation[];
    };
}

export interface RecoveryDashboardData {
    snapshot: RecoverySnapshot | null;
    trend: RecoveryTrendPoint[];
    habits: RecoveryHabit[];
    recommendations: RecoveryRecommendation[];
}

interface HabitsResponse {
    habits?: RecoveryHabit[];
    items?: RecoveryHabit[];
    data?: RecoveryHabit[];
}

interface UserHabitsResponse {
    habits?: RecoveryHabit[];
    items?: RecoveryHabit[];
    data?: RecoveryHabit[];
}

interface ErrorResponse {
    message?: string;
    error?: string;
}

async function request<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const controller =
        new AbortController();

    const timeout =
        window.setTimeout(
            () => {
                controller.abort();
            },
            10000
        );

    const headers =
        new Headers(
            options.headers
        );

    headers.set(
        "Accept",
        "application/json"
    );

    if (
        options.body &&
        !headers.has(
            "Content-Type"
        )
    ) {
        headers.set(
            "Content-Type",
            "application/json"
        );
    }

    try {
        const response =
            await fetch(
                url,
                {
                    ...options,
                    credentials:
                        "same-origin",
                    headers,
                    signal:
                        controller.signal
                }
            );

        const body =
            await response.text();

        let data: unknown = null;

        if (body.trim()) {
            try {
                data =
                    JSON.parse(
                        body
                    );
            } catch {
                throw new Error(
                    translate(
                        "recovery",
                        "request.invalidJson"
                    )
                );
            }
        }

        if (!response.ok) {
            const errorData =
                data as ErrorResponse | null;

            throw new Error(
                errorData?.message ||
                errorData?.error ||
                `HTTP ${response.status}`
            );
        }

        return data as T;
    } catch (error) {
        if (
            error instanceof DOMException &&
            error.name === "AbortError"
        ) {
            throw new Error(
                translate(
                    "recovery",
                    "request.timeout"
                )
            );
        }

        throw error;
    } finally {
        window.clearTimeout(
            timeout
        );
    }
}

function normalizeHabits(
    data:
        | RecoveryHabit[]
        | HabitsResponse
        | UserHabitsResponse
        | null
): RecoveryHabit[] {
    if (Array.isArray(data)) {
        return data;
    }

    if (!data) {
        return [];
    }

    return (
        data.habits ??
        data.items ??
        data.data ??
        []
    );
}

export const RecoveryAPI = {
    async getSnapshot(
        userId: number
    ): Promise<RecoverySnapshot | null> {
        const data =
            await request<
                RecoverySnapshot |
                {
                    snapshot?:
                        RecoverySnapshot |
                        null;
                } |
                null
            >(
                `/api/recovery/snapshot/${userId}`
            );

        if (
            data &&
            !Array.isArray(data) &&
            "snapshot" in data
        ) {
            return data.snapshot ?? null;
        }

        return data as RecoverySnapshot | null;
    },

    async getHeatmap(
        userId: number,
        year: number
    ): Promise<RecoveryHeatmapResponse> {
        return request<
            RecoveryHeatmapResponse
        >(
            `/api/recovery/heatmap/${userId}?year=${year}`
        );
    },

    async getTrend(
        userId: number
    ): Promise<RecoveryTrendPoint[]> {
        const data =
            await request<
                RecoveryTrendPoint[] |
                {
                    trend?: RecoveryTrendPoint[];
                    data?: RecoveryTrendPoint[];
                }
            >(
                `/api/recovery/trend/${userId}`
            );

        if (Array.isArray(data)) {
            return data;
        }

        return (
            data.trend ??
            data.data ??
            []
        );
    },

    async getHabitsList(): Promise<RecoveryHabit[]> {
        const data =
            await request<
                RecoveryHabit[] |
                HabitsResponse
            >(
                "/api/recovery/habits/list"
            );

        return normalizeHabits(
            data
        );
    },

    async getUserHabits(
        userId: number
    ): Promise<RecoveryHabit[]> {
        const data =
            await request<
                RecoveryHabit[] |
                UserHabitsResponse
            >(
                `/api/recovery/habits/user/${userId}`
            );

        return normalizeHabits(
            data
        );
    },

    async getHabits(
        userId: number
    ): Promise<RecoveryHabit[]> {
        return this.getUserHabits(
            userId
        );
    },

    async addHabit(
        userId: number,
        habitId: number | string
    ): Promise<unknown> {
        return request<unknown>(
            `/api/recovery/habits/add/${habitId}`,
            {
                method: "POST",
                body: JSON.stringify({
                    user_id: userId
                })
            }
        );
    },

    async removeHabit(
        userHabitId: number | string
    ): Promise<unknown> {
        return request<unknown>(
            `/api/recovery/habits/${userHabitId}`,
            {
                method: "DELETE"
            }
        );
    },

    async deleteHabit(
        userHabitId: number | string
    ): Promise<unknown> {
        return this.removeHabit(
            userHabitId
        );
    },

    async getRecommendations(
        userId: number
    ): Promise<RecoveryRecommendationsResponse> {
        return request<
            RecoveryRecommendationsResponse
        >(
            `/api/recovery/recommendations/${userId}`
        );
    },

    async getDashboard(
        userId: number
    ): Promise<RecoveryDashboardData> {
        const [
            snapshot,
            trend,
            habits,
            recommendations
        ] = await Promise.all([
            this.getSnapshot(
                userId
            ),
            this.getTrend(
                userId
            ),
            this.getHabits(
                userId
            ),
            this.getRecommendations(
                userId
            )
        ]);

        const recommendationData =
            recommendations.recommendations;

        return {
            snapshot,
            trend,
            habits,
            recommendations:
                Array.isArray(
                    recommendationData
                )
                    ? recommendationData
                    : recommendationData
                        ?.items ?? []
        };
    },

    async addSleep(
        userId: number,
        sleepStart: string,
        sleepEnd: string
    ): Promise<unknown> {
        return request<unknown>(
            "/api/recovery/sleep",
            {
                method: "POST",
                body: JSON.stringify({
                    user_id: userId,
                    sleep_start: sleepStart,
                    sleep_end: sleepEnd
                })
            }
        );
    },

    async getDayDetails(
        userId: number,
        date: string
    ): Promise<RecoveryDayDetails | null> {
        return request<
            RecoveryDayDetails | null
        >(
            `/api/recovery/day-details/${userId}?date=${encodeURIComponent(date)}`
        );
    },

    async logHabit(
        userHabitId: number | string
    ): Promise<unknown> {
        return request<unknown>(
            "/api/recovery/habits/logs",
            {
                method: "POST",
                body: JSON.stringify({
                    user_habit_id:
                        userHabitId
                })
            }
        );
    },

    async unlogHabit(
        userHabitId: number | string
    ): Promise<unknown> {
        return request<unknown>(
            `/api/recovery/habits/logs/${userHabitId}`,
            {
                method: "DELETE"
            }
        );
    }
};