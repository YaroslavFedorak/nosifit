import type {
    RecoveryHabit,
    RecoverySnapshot
} from "../../widgets/recovery/state.js";

const API_BASE =
    "/api/recovery";

const DEFAULT_TIMEOUT_MS =
    10000;

interface RecoverySnapshotResponse {
    snapshot: RecoverySnapshot | null;
}

async function request<T>(
    url: string,
    options: RequestInit = {},
    timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
    const controller =
        new AbortController();

    const timeoutId =
        window.setTimeout(
            () => controller.abort(),
            timeoutMs
        );

    try {
        const response =
            await fetch(
                url,
                {
                    headers: {
                        "Content-Type":
                            "application/json",
                        ...(options.headers || {})
                    },
                    signal:
                        controller.signal,
                    ...options
                }
            );

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
                        typeof error.error ===
                            "string"
                    ) {
                        message =
                            error.error;
                    }
                } else {
                    const text =
                        await response.text();

                    if (text) {
                        message =
                            text;
                    }
                }
            } catch {}

            throw new Error(
                message
            );
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
            return await response.json() as T;
        }

        return null as T;
    } catch (error: unknown) {
        if (
            error instanceof DOMException &&
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
        userId: number | string
    ) =>
        `${API_BASE}/snapshot/${userId}`,

    sleep:
        () =>
            `${API_BASE}/sleep`,

    addHabit: (
        habitId: number | string
    ) =>
        `${API_BASE}/habits/add/${habitId}`,

    removeHabit: (
        userHabitId: number | string
    ) =>
        `${API_BASE}/habits/${userHabitId}`,

    logHabit:
        () =>
            `${API_BASE}/habits/logs`,

    habitsList:
        () =>
            `${API_BASE}/habits/list`,

    userHabits: (
        userId: number | string
    ) =>
        `${API_BASE}/habits/user/${userId}`
};

function isSnapshotResponse(
    value: unknown
): value is RecoverySnapshotResponse {
    return (
        typeof value === "object" &&
        value !== null &&
        "snapshot" in value
    );
}

function isRecoverySnapshot(
    value: unknown
): value is RecoverySnapshot {
    return (
        typeof value === "object" &&
        value !== null
    );
}

export const RecoveryAPI = {
    async getSnapshot(
        userId: number | string
    ): Promise<RecoverySnapshot | null> {
        const response =
            await request<unknown>(
                ENDPOINTS.snapshot(
                    userId
                )
            );

        if (
            isSnapshotResponse(
                response
            )
        ) {
            return (
                response.snapshot
            );
        }

        if (
            isRecoverySnapshot(
                response
            )
        ) {
            return response;
        }

        return null;
    },

    getUserHabits(
        userId: number | string
    ): Promise<RecoveryHabit[]> {
        return request<
            RecoveryHabit[]
        >(
            ENDPOINTS.userHabits(
                userId
            )
        );
    },

    addSleep(
        userId: number | string,
        sleepStart: string,
        sleepEnd: string
    ) {
        return request<unknown>(
            ENDPOINTS.sleep(),
            {
                method: "POST",
                body: JSON.stringify({
                    user_id:
                        userId,
                    sleep_start:
                        sleepStart,
                    sleep_end:
                        sleepEnd
                })
            }
        );
    },

    addHabit(
        userId: number | string,
        habitId: number | string
    ) {
        return request<unknown>(
            ENDPOINTS.addHabit(
                habitId
            ),
            {
                method: "POST",
                body: JSON.stringify({
                    user_id:
                        userId
                })
            }
        );
    },

    removeHabit(
        userHabitId:
            number | string
    ) {
        return request<unknown>(
            ENDPOINTS.removeHabit(
                userHabitId
            ),
            {
                method: "DELETE"
            }
        );
    },

    logHabit(
        userHabitId:
            number | string
    ) {
        return request<unknown>(
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

    getHabitsList() {
        return request<
            RecoveryHabit[]
        >(
            ENDPOINTS.habitsList()
        );
    }
};