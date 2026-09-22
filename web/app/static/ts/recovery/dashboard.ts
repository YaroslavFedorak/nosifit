import { RecoveryAPI } from "./api.js";
import { renderSleepWidget } from "./sleep.js";
import { renderHabitsWidget } from "./habits.js";
import { renderHeatmapWidget } from "./heatmap/heatmap.js";
import { renderRecommendationsWidget } from "./recommendations.js";
import { renderScoreWidget } from "./score.js";

import type {
    RecoveryHeatmapResponse,
    RecoveryHabit,
    RecoveryRecommendationsResponse,
    RecoverySnapshot
} from "./api.js";

import type {
    RecommendationsData,
    Recommendation
} from "./recommendations.js";

interface RecoveryState {
    snapshot: RecoverySnapshot | null;
    habits: RecoveryHabit[];
    heatmap: RecoveryHeatmapResponse | null;
    recommendations: RecoveryRecommendationsResponse | null;
    firstLoad: boolean;
}

const state: RecoveryState = {
    snapshot: null,
    habits: [],
    heatmap: null,
    recommendations: null,
    firstLoad: true
};

function getUserId(): number | null {
    const app =
        document.getElementById(
            "recovery-app"
        );

    if (!app) {
        return null;
    }

    const userId =
        Number(
            app.dataset.userId
        );

    return Number.isFinite(userId) &&
        userId > 0
        ? userId
        : null;
}

function normalizeRecommendations(
    data: RecoveryRecommendationsResponse | null
): RecommendationsData | null {
    if (!data) {
        return null;
    }

    const raw =
        data.recommendations;

    if (Array.isArray(raw)) {
        const recommendations: Recommendation[] = [];

        raw.forEach(item => {
            if (
                typeof item === "object" &&
                item !== null
            ) {
                const value =
                    item as Record<string, unknown>;

                recommendations.push({
                    type:
                        typeof value.type === "string"
                            ? value.type
                            : undefined,
                    text:
                        typeof value.text === "string"
                            ? value.text
                            : undefined,
                    priority:
                        typeof value.priority === "string"
                            ? value.priority
                            : undefined
                });
            }
        });

        return {
            recommendations
        };
    }

    if (
        typeof raw === "object" &&
        raw !== null
    ) {
        const value =
            raw as Record<string, unknown>;

        if (Array.isArray(value.items)) {
            const recommendations: Recommendation[] = [];

            value.items.forEach(item => {
                if (
                    typeof item === "object" &&
                    item !== null
                ) {
                    const recommendation =
                        item as Record<string, unknown>;

                    recommendations.push({
                        type:
                            typeof recommendation.type === "string"
                                ? recommendation.type
                                : undefined,
                        text:
                            typeof recommendation.text === "string"
                                ? recommendation.text
                                : undefined,
                        priority:
                            typeof recommendation.priority === "string"
                                ? recommendation.priority
                                : undefined
                    });
                }
            });

            return {
                recommendations
            };
        }
    }

    return {
        recommendations: []
    };
}

function renderLoading(): void {
    renderSleepWidget(
        null,
        {
            loading: true
        }
    );

    renderHabitsWidget(
        null,
        {
            loading: true
        }
    );

    renderScoreWidget(
        null,
        {
            loading: true
        }
    );

    renderHeatmapWidget(
        null,
        {
            loading: true
        }
    );

    renderRecommendationsWidget(
        null,
        {
            loading: true
        }
    );
}

function renderAll(): void {
    renderSleepWidget(
        state.snapshot
    );

    renderHabitsWidget(
        state.habits
    );

    renderScoreWidget(
        state.snapshot
    );

    renderHeatmapWidget(
        state.heatmap
    );

    const recommendations =
        normalizeRecommendations(
            state.recommendations
        );

    renderRecommendationsWidget(
        recommendations
    );
}

export async function refreshRecoveryDashboard(
    userId?: number
): Promise<void> {
    const resolvedUserId =
        userId ?? getUserId();

    if (
        resolvedUserId === null
    ) {
        return;
    }

    if (
        state.firstLoad
    ) {
        renderLoading();
    }

    const [
        snapshotResult,
        habitsResult,
        heatmapResult,
        recommendationsResult
    ] = await Promise.allSettled([
        RecoveryAPI.getSnapshot(
            resolvedUserId
        ),
        RecoveryAPI.getHabits(
            resolvedUserId
        ),
        RecoveryAPI.getHeatmap(
            resolvedUserId,
            new Date().getFullYear()
        ),
        RecoveryAPI.getRecommendations(
            resolvedUserId
        )
    ]);

    state.snapshot =
        snapshotResult.status === "fulfilled"
            ? snapshotResult.value
            : null;

    state.habits =
        habitsResult.status === "fulfilled"
            ? habitsResult.value
            : [];

    state.heatmap =
        heatmapResult.status === "fulfilled"
            ? heatmapResult.value
            : null;

    state.recommendations =
        recommendationsResult.status === "fulfilled"
            ? recommendationsResult.value
            : null;

    state.firstLoad = false;

    renderAll();
}

export async function initRecoveryDashboard(
    userId?: number
): Promise<void> {
    await refreshRecoveryDashboard(
        userId
    );
}

export function destroyRecoveryDashboard(): void {
    state.snapshot = null;
    state.habits = [];
    state.heatmap = null;
    state.recommendations = null;
    state.firstLoad = true;
}
