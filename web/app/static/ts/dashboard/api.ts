import { TrainingAPI } from "./widgets/training/api.js";
import { RecoveryAPI } from "./modals/recovery/api.js";

const API_BASE = "/api/dashboard";

async function jsonFetch(
    url: string,
    options: RequestInit = {}
): Promise<any> {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            Accept: "application/json",
            ...(options.body
                ? {
                    "Content-Type":
                        "application/json"
                }
                : {}),
            ...(options.headers || {})
        },
        cache: "no-store",
        ...options
    });

    let data: any = null;

    try {
        data =
            await response.json();
    } catch (_) {
        data = null;
    }

    if (!response.ok) {
        console.error(
            `Dashboard API error: ${response.status} ${url}`,
            data
        );

        throw new Error(
            data?.message ||
            data?.error ||
            `HTTP ${response.status}`
        );
    }

    return data;
}

export function getToday(): Promise<any> {
    return jsonFetch(
        `${API_BASE}/today`
    );
}

export function getHeatmap(): Promise<any> {
    return jsonFetch(
        `${API_BASE}/heatmap`
    );
}

export function getDay(
    date: string
): Promise<any> {
    return jsonFetch(
        `${API_BASE}/day/${encodeURIComponent(date)}`
    );
}

export function getRecommendation(): Promise<any> {
    return jsonFetch(
        `${API_BASE}/recommendation`
    );
}

export function getExercises(
    params: Record<string, string> = {}
): Promise<any> {
    return TrainingAPI.getExercises(
        params
    );
}

export function getRecoveryHabits(): Promise<any> {
    return RecoveryAPI.getHabitsList();
}

export function getUserRecoveryHabits(
    userId: string | number
): Promise<any> {
    return RecoveryAPI.getUserHabits(
        userId
    );
}

export function addRecoveryHabit(
    userId: string | number,
    habitId: string | number
): Promise<any> {
    return RecoveryAPI.addHabit(
        userId,
        habitId
    );
}

export function addSleep(
    userId: string | number,
    sleepStart: string,
    sleepEnd: string
): Promise<any> {
    return RecoveryAPI.addSleep(
        userId,
        sleepStart,
        sleepEnd
    );
}

export const DashboardAPI = {
    getToday,
    getHeatmap,
    getDay,
    getRecommendation,
    getExercises,
    getRecoveryHabits,
    getUserRecoveryHabits,
    addRecoveryHabit,
    addSleep
};