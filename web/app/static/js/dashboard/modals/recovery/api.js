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
                        typeof error.error ===
                            "string") {
                        message =
                            error.error;
                    }
                }
                else {
                    const text = await response.text();
                    if (text) {
                        message =
                            text;
                    }
                }
            }
            catch { }
            throw new Error(message);
        }
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            return await response.json();
        }
        return null;
    }
    catch (error) {
        if (error instanceof DOMException &&
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
    snapshot: (userId) => `${API_BASE}/snapshot/${userId}`,
    sleep: () => `${API_BASE}/sleep`,
    addHabit: (habitId) => `${API_BASE}/habits/add/${habitId}`,
    removeHabit: (userHabitId) => `${API_BASE}/habits/${userHabitId}`,
    logHabit: () => `${API_BASE}/habits/logs`,
    habitsList: () => `${API_BASE}/habits/list`,
    userHabits: (userId) => `${API_BASE}/habits/user/${userId}`
};
function isSnapshotResponse(value) {
    return (typeof value === "object" &&
        value !== null &&
        "snapshot" in value);
}
function isRecoverySnapshot(value) {
    return (typeof value === "object" &&
        value !== null);
}
export const RecoveryAPI = {
    async getSnapshot(userId) {
        const response = await request(ENDPOINTS.snapshot(userId));
        if (isSnapshotResponse(response)) {
            return (response.snapshot);
        }
        if (isRecoverySnapshot(response)) {
            return response;
        }
        return null;
    },
    getUserHabits(userId) {
        return request(ENDPOINTS.userHabits(userId));
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
    }
};
