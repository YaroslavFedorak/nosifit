const API_BASE = "/api/recovery";
const DEFAULT_TIMEOUT_MS = 10000;
async function request(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            signal: controller.signal,
            ...options
        });
        if (!response.ok) {
            let message = `HTTP ${response.status}`;
            try {
                const contentType = response.headers.get("content-type") || "";
                if (contentType.includes("application/json")) {
                    const error = await response.json();
                    if (error &&
                        error.error) {
                        message =
                            error.error;
                    }
                }
                else {
                    const text = await response.text();
                    if (text) {
                        message = text;
                    }
                }
            }
            catch (_) { }
            throw new Error(message);
        }
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            return await response.json();
        }
        return null;
    }
    catch (error) {
        if (error &&
            error.name === "AbortError") {
            throw new Error("Request timeout");
        }
        throw error;
    }
    finally {
        window.clearTimeout(timeoutId);
    }
}
const ENDPOINTS = {
    snapshot: (userId, date) => date
        ? `${API_BASE}/snapshot/${userId}?date=${encodeURIComponent(date)}`
        : `${API_BASE}/snapshot/${userId}`,
    heatmap: (userId, year) => `${API_BASE}/heatmap/${userId}?year=${year}`,
    recommendations: (userId) => `${API_BASE}/recommendations/${userId}`,
    sleep: () => `${API_BASE}/sleep`,
    addHabit: (habitId) => `${API_BASE}/habits/add/${habitId}`,
    removeHabit: (userHabitId) => `${API_BASE}/habits/${userHabitId}`,
    logHabit: () => `${API_BASE}/habits/logs`,
    habitsList: () => `${API_BASE}/habits/list`,
    userHabits: (userId) => `${API_BASE}/habits/user/${userId}`,
    dayDetails: (userId, date) => `${API_BASE}/day-details/${userId}?date=${encodeURIComponent(date)}`
};
export const RecoveryAPI = {
    getSnapshot(userId, date = null) {
        return request(ENDPOINTS.snapshot(userId, date));
    },
    getHeatmap(userId, year) {
        return request(ENDPOINTS.heatmap(userId, year));
    },
    getRecommendations(userId) {
        return request(ENDPOINTS.recommendations(userId));
    },
    addSleep(userId, sleepStart, sleepEnd) {
        return request(ENDPOINTS.sleep(), {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                sleep_start: sleepStart,
                sleep_end: sleepEnd
            })
        });
    },
    addHabit(userId, habitId) {
        return request(ENDPOINTS.addHabit(habitId), {
            method: "POST",
            body: JSON.stringify({
                user_id: userId
            })
        });
    },
    removeHabit(userHabitId) {
        return request(ENDPOINTS.removeHabit(userHabitId), {
            method: "DELETE"
        });
    },
    logHabit(userHabitId) {
        return request(ENDPOINTS.logHabit(), {
            method: "POST",
            body: JSON.stringify({
                user_habit_id: userHabitId
            })
        });
    },
    getHabitsList() {
        return request(ENDPOINTS.habitsList());
    },
    getUserHabits(userId) {
        return request(ENDPOINTS.userHabits(userId));
    },
    getDayDetails(userId, date) {
        return request(ENDPOINTS.dayDetails(userId, date));
    }
};
