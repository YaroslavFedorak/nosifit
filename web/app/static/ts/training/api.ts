const BASE = "/api/training";

export type ExercisePrescription = {
    sets?: number;
    reps_min?: number;
    reps_max?: number;
    seconds_min?: number;
    seconds_max?: number;
    per_side?: boolean;
};

export type Exercise = {
    id: number | string;
    name: string;
    slug?: string;
    muscles_primary?: string[];
    measurement_type?: "reps" | "duration";
    prescription?: ExercisePrescription | null;
    [key: string]: unknown;
};

export type ExercisesResponse =
    | Exercise[]
    | {
        items?: Exercise[];
    };

export type WorkoutExercise = {
    exercise: Exercise;
    sets: number;
    reps: string | number | null;
    duration_sec?: number | null;
    load: number;
    // Stored effort of a saved exercise (e.g. RIR from Telegram), sent
    // back unchanged on the next save.
    rpe?: number | null;
    done: boolean;
    fromPlan: boolean;
};

export type LoggedExercise = {
    id: number | string;
    slug?: string;
    name: string;
    measurement_type?: "reps" | "duration";
    sets: number;
    reps: string | null;
    duration_sec: number | null;
    load: number | null;
    rpe: number | null;
};

export type LoggedTodayResponse = {
    session: {
        id: number;
        exercises: LoggedExercise[];
    } | null;
};

export type WeeklyMuscleSets = {
    muscle: string;
    sets: number;
    target_sets: number;
};

export type WeeklySets = {
    week_start: string;
    week_end: string;
    muscles: WeeklyMuscleSets[];
};

export type AnalyticsData = {
    weekly_sets?: WeeklySets | null;
    [key: string]: unknown;
};

export type HeatmapDay = {
    date?: string;
    // Relative intensity of the day vs the user's typical session (0-100).
    intensity_percent?: number | null;
    hard_sets?: number | null;
    session_training_stress_proxy?: number | null;
    is_today?: boolean;
    [key: string]: unknown;
};

export type HeatmapResponse = {
    days?: HeatmapDay[];
    [key: string]: unknown;
};

export type SessionExercise = {
    name: string;
    slug?: string;
    measurement_type?: "reps" | "duration";
    sets: number;
    reps: number | string | null;
    duration_sec?: number | null;
    per_side?: boolean;
    load: number;
    [key: string]: unknown;
};

export type DaySession = {
    exercises?: SessionExercise[];
    [key: string]: unknown;
};

export type DayDetailsResponse = {
    sessions?: DaySession[];
    [key: string]: unknown;
};

export type JsonObject = Record<string, unknown>;

export type PlanExercise = {
    exercise: Exercise;
    sets: number;
    reps: string | number | null;
    duration_sec?: number | null;
    load: number;
};

export type PlanDayKey =
    | "mon"
    | "tue"
    | "wed"
    | "thu"
    | "fri"
    | "sat"
    | "sun";

export type PlanDays = Record<
    PlanDayKey,
    PlanExercise[]
>;

export type TrainingPlan = {
    id?: number | string;
    name?: string;
    is_active?: boolean;
    days?: Partial<PlanDays>;
    [key: string]: unknown;
};

export type PlansResponse =
    | TrainingPlan[]
    | {
        items?: TrainingPlan[];
        plans?: TrainingPlan[];
    };

export type RecommendationItem = {
    exercise?: string;
    reasons?: string[];
};

export type MuscleData = {
    weak?: string[];
    balanced?: string[];
    overloaded?: string[];
};

export type RecommendationsData = {
    muscles?: MuscleData;
    recommended_exercises?: RecommendationItem[];
    [key: string]: unknown;
};

async function jsonFetch<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    let data: unknown = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        const message =
            typeof data === "object" &&
            data !== null &&
            "message" in data &&
            typeof data.message === "string"
                ? data.message
                : `HTTP ${response.status}`;

        throw new Error(message);
    }

    return data as T;
}

type ExercisesPage = {
    items?: Exercise[];
    total?: number;
};

// The API caps page size, so a call without an explicit page walks every
// page and returns the whole catalog.
const EXERCISES_PAGE_SIZE = 100;
const EXERCISES_MAX_PAGES = 20;

export const TrainingAPI = {
    async getExercises(
        params: Record<string, string | number | boolean> = {}
    ): Promise<ExercisesResponse> {
        const buildUrl = (
            values: Record<string, string | number | boolean>
        ): string => {
            const query = new URLSearchParams(
                Object.entries(values).map(
                    ([key, value]) => [key, String(value)]
                )
            ).toString();

            return query
                ? `${BASE}/exercises?${query}`
                : `${BASE}/exercises`;
        };

        if ("page" in params) {
            return jsonFetch<ExercisesResponse>(
                buildUrl(params)
            );
        }

        const items: Exercise[] = [];

        for (
            let page = 1;
            page <= EXERCISES_MAX_PAGES;
            page += 1
        ) {
            const data =
                await jsonFetch<ExercisesPage>(
                    buildUrl({
                        ...params,
                        page,
                        per_page: EXERCISES_PAGE_SIZE
                    })
                );

            const pageItems =
                data.items ?? [];

            items.push(...pageItems);

            if (
                pageItems.length < EXERCISES_PAGE_SIZE ||
                items.length >= (data.total ?? 0)
            ) {
                break;
            }
        }

        return { items };
    },

    getPlans(): Promise<PlansResponse> {
        return jsonFetch<PlansResponse>(
            `${BASE}/plans`
        );
    },

    savePlan(
        payload: TrainingPlan
    ): Promise<TrainingPlan> {
        return jsonFetch<TrainingPlan>(
            `${BASE}/plans`,
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
    },

    updatePlan(
        id: number | string,
        payload: TrainingPlan
    ): Promise<TrainingPlan> {
        return jsonFetch<TrainingPlan>(
            `${BASE}/plans/${id}`,
            {
                method: "PUT",
                body: JSON.stringify(payload)
            }
        );
    },

    deletePlan(
        id: number | string
    ): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/plans/${id}`,
            {
                method: "DELETE"
            }
        );
    },

    completeSession(
        payload: JsonObject
    ): Promise<{
        id: number | string;
        [key: string]: unknown;
    }> {
        return jsonFetch(
            `${BASE}/sessions/complete`,
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
    },

    startSession(
        payload: JsonObject
    ): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/sessions/start`,
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
    },

    finishSession(
        sessionId: number | string,
        payload: JsonObject
    ): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/sessions/${sessionId}/finish`,
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
    },

    updateSessionExercise(
        sessionId: number | string,
        exerciseId: number | string,
        payload: JsonObject
    ): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/sessions/${sessionId}/exercise/${exerciseId}`,
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
    },

    getAnalytics(): Promise<AnalyticsData> {
        return jsonFetch<AnalyticsData>(
            `${BASE}/analytics`
        );
    },

    getRecommendations(): Promise<RecommendationsData> {
        return jsonFetch<RecommendationsData>(
            `${BASE}/recommendations`
        );
    },

    getHeatmap(
        year = new Date().getFullYear()
    ): Promise<HeatmapResponse> {
        return jsonFetch<HeatmapResponse>(
            `${BASE}/heatmap?year=${year}`
        );
    },

    getToday(): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/today`
        );
    },

    getLoggedToday(): Promise<LoggedTodayResponse> {
        return jsonFetch<LoggedTodayResponse>(
            `${BASE}/sessions/today`
        );
    },

    getTodaySession(): Promise<JsonObject> {
        return jsonFetch<JsonObject>(
            `${BASE}/today-session`
        );
    },

    getDayDetails(
        date: string
    ): Promise<DayDetailsResponse> {
        return jsonFetch<DayDetailsResponse>(
            `${BASE}/day/${date}`
        );
    }
};