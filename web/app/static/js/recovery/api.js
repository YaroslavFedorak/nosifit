import { translate } from "../i18n/loader.js";
async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
        controller.abort();
    }, 10000);
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");
    if (options.body &&
        !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    try {
        const response = await fetch(url, {
            ...options,
            credentials: "same-origin",
            headers,
            signal: controller.signal
        });
        const body = await response.text();
        let data = null;
        if (body.trim()) {
            try {
                data =
                    JSON.parse(body);
            }
            catch {
                throw new Error(translate("recovery", "request.invalidJson"));
            }
        }
        if (!response.ok) {
            const errorData = data;
            throw new Error(errorData?.message ||
                errorData?.error ||
                `HTTP ${response.status}`);
        }
        return data;
    }
    catch (error) {
        if (error instanceof DOMException &&
            error.name === "AbortError") {
            throw new Error(translate("recovery", "request.timeout"));
        }
        throw error;
    }
    finally {
        window.clearTimeout(timeout);
    }
}
function normalizeHabits(data) {
    if (Array.isArray(data)) {
        return data;
    }
    if (!data) {
        return [];
    }
    return (data.habits ??
        data.items ??
        data.data ??
        []);
}
export const RecoveryAPI = {
    async getSnapshot(userId) {
        const data = await request(`/api/recovery/snapshot/${userId}`);
        if (data &&
            !Array.isArray(data) &&
            "snapshot" in data) {
            return data.snapshot ?? null;
        }
        return data;
    },
    async getHeatmap(userId, year) {
        return request(`/api/recovery/heatmap/${userId}?year=${year}`);
    },
    async getTrend(userId) {
        const data = await request(`/api/recovery/trend/${userId}`);
        if (Array.isArray(data)) {
            return data;
        }
        return (data.trend ??
            data.data ??
            []);
    },
    async getHabitsList() {
        const data = await request("/api/recovery/habits/list");
        return normalizeHabits(data);
    },
    async getUserHabits(userId) {
        const data = await request(`/api/recovery/habits/user/${userId}`);
        return normalizeHabits(data);
    },
    async getHabits(userId) {
        return this.getUserHabits(userId);
    },
    async addHabit(userId, habitId) {
        return request(`/api/recovery/habits/add/${habitId}`, {
            method: "POST",
            body: JSON.stringify({
                user_id: userId
            })
        });
    },
    async removeHabit(userHabitId) {
        return request(`/api/recovery/habits/${userHabitId}`, {
            method: "DELETE"
        });
    },
    async deleteHabit(userHabitId) {
        return this.removeHabit(userHabitId);
    },
    async getRecommendations(userId) {
        return request(`/api/recovery/recommendations/${userId}`);
    },
    async getDashboard(userId) {
        const [snapshot, trend, habits, recommendations] = await Promise.all([
            this.getSnapshot(userId),
            this.getTrend(userId),
            this.getHabits(userId),
            this.getRecommendations(userId)
        ]);
        const recommendationData = recommendations.recommendations;
        return {
            snapshot,
            trend,
            habits,
            recommendations: Array.isArray(recommendationData)
                ? recommendationData
                : recommendationData
                    ?.items ?? []
        };
    },
    async addSleep(userId, sleepStart, sleepEnd) {
        return request("/api/recovery/sleep", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                sleep_start: sleepStart,
                sleep_end: sleepEnd
            })
        });
    },
    async getDayDetails(userId, date) {
        return request(`/api/recovery/day-details/${userId}?date=${encodeURIComponent(date)}`);
    },
    async logHabit(userHabitId) {
        return request("/api/recovery/habits/logs", {
            method: "POST",
            body: JSON.stringify({
                user_habit_id: userHabitId
            })
        });
    },
    async unlogHabit(userHabitId) {
        return request(`/api/recovery/habits/logs/${userHabitId}`, {
            method: "DELETE"
        });
    }
};
