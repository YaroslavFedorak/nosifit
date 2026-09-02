async function jsonFetch(
    url,
    options = {}
) {
    const response =
        await fetch(
            url,
            {
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
            }
        );

    let data = null;

    try {
        data = await response.json();
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

export function getToday() {
    return jsonFetch("/api/dashboard/today");
}

export function getHeatmap() {
    return jsonFetch("/api/dashboard/heatmap");
}

export function getDay(date) {
    return jsonFetch(`/api/dashboard/day/${date}`);
}

export function getRecommendation() {
    return jsonFetch("/api/dashboard/recommendation");
}

import { TrainingAPI } from "../training/api.js";

export function getExercises(params = {}) {
    return TrainingAPI.getExercises(params);
}

export const DashboardAPI = {
    getToday,
    getHeatmap,
    getDay,
    getRecommendation,
    getExercises
};
