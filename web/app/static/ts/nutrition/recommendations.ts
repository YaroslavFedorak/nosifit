import {
    nutrition_t,
} from "../i18n/index.js";


type RecommendationType =
    | "calories"
    | "protein"
    | "fat"
    | "carbs"
    | "quality"
    | "balance"
    | "protein_progress"
    | "macro_balance";


type RecommendationPriority =
    | "low"
    | "medium"
    | "high";


interface NutritionRecommendation {
    type: RecommendationType;
    title_key: string;
    message_key: string;
    params: Record<string, string | number>;
    priority: RecommendationPriority;
}


interface NutritionRecommendationSummary {
    calories: number;
    calories_goal: number;

    protein: number;
    protein_goal: number;

    fat: number;
    fat_goal: number;

    carbs: number;
    carbs_goal: number;

    quality_score: number;

    day_progress:
        | "morning"
        | "day"
        | "evening"
        | "late";
}


interface NutritionRecommendationResponse {
    recommendations: NutritionRecommendation[];
    summary: NutritionRecommendationSummary;
}


async function fetchNutritionRecommendations(): Promise<NutritionRecommendationResponse> {
    const response =
        await fetch(
            "/api/nutrition/recommendations",
            {
                credentials: "same-origin",
            },
        );

    if (!response.ok) {
        throw new Error(
            "Failed to fetch nutrition recommendations",
        );
    }

    return response.json() as Promise<NutritionRecommendationResponse>;
}


function getPriorityClass(
    priority: RecommendationPriority,
): string {
    return `recommendation-item--${priority}`;
}


function getRecommendationParams(
    params: Record<string, string | number>,
): Record<string, string | number> {
    const localizedParams = {
        ...params,
    };

    if (
        typeof params.macro === "string"
    ) {
        localizedParams.macro =
            nutrition_t(
                `recommendations.macro.${params.macro}`,
            );
    }

    if (
        typeof params.direction === "string"
    ) {
        localizedParams.direction =
            nutrition_t(
                `recommendations.direction.${params.direction}`,
            );
    }

    return localizedParams;
}


function renderRecommendation(
    recommendation: NutritionRecommendation,
): HTMLDivElement {
    const element =
        document.createElement("div");

    element.className = [
        "recommendation-item",
        getPriorityClass(
            recommendation.priority,
        ),
    ].join(" ");

    const params =
        getRecommendationParams(
            recommendation.params,
        );

    element.innerHTML = `
        <div class="recommendation-marker"></div>

        <div class="recommendation-content">
            <div class="recommendation-title">
                ${nutrition_t(
                    recommendation.title_key,
                    params,
                )}
            </div>

            <div class="recommendation-text">
                ${nutrition_t(
                    recommendation.message_key,
                    params,
                )}
            </div>
        </div>
    `;

    return element;
}


function renderEmptyRecommendations(
    container: HTMLElement,
): void {
    container.innerHTML = `
        <div class="recommendation-item recommendation-item--low">
            <div class="recommendation-marker"></div>

            <div class="recommendation-content">
                <div class="recommendation-title">
                    ${nutrition_t(
                        "recommendations.empty.title",
                    )}
                </div>

                <div class="recommendation-text">
                    ${nutrition_t(
                        "recommendations.empty.message",
                    )}
                </div>
            </div>
        </div>
    `;
}


function renderRecommendations(
    recommendations: NutritionRecommendation[],
): void {
    const container =
        document.querySelector<HTMLElement>(
            "[data-nutrition-recommendations]",
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (
        recommendations.length === 0
    ) {
        renderEmptyRecommendations(
            container,
        );

        return;
    }

    for (
        const recommendation
        of recommendations
    ) {
        container.appendChild(
            renderRecommendation(
                recommendation,
            ),
        );
    }
}


function renderSummary(
    summary: NutritionRecommendationSummary,
): void {
    const container =
        document.querySelector<HTMLElement>(
            "[data-nutrition-recommendations-summary]",
        );

    if (!container) {
        return;
    }

    const calorieRemaining =
        Math.max(
            summary.calories_goal
            - summary.calories,
            0,
        );

    const proteinRemaining =
        Math.max(
            summary.protein_goal
            - summary.protein,
            0,
        );

    const kcal =
        nutrition_t(
            "units.kcal",
        );

    const grams =
        nutrition_t(
            "units.grams",
        );

    container.innerHTML = `
        <div class="recommendations-summary-row">
            <span>
                ${nutrition_t(
                    "stats.calories",
                )}
            </span>

            <span>
                ${Math.round(
                    summary.calories,
                )}
                /
                ${Math.round(
                    summary.calories_goal,
                )}
                ${kcal}
            </span>
        </div>

        <div class="recommendations-summary-row">
            <span>
                ${nutrition_t(
                    "stats.protein",
                )}
            </span>

            <span>
                ${summary.protein.toFixed(1)}
                /
                ${summary.protein_goal.toFixed(1)}
                ${grams}
            </span>
        </div>

        <div class="recommendations-summary-row">
            <span>
                ${nutrition_t(
                    "stats.fat",
                )}
            </span>

            <span>
                ${summary.fat.toFixed(1)}
                /
                ${summary.fat_goal.toFixed(1)}
                ${grams}
            </span>
        </div>

        <div class="recommendations-summary-row">
            <span>
                ${nutrition_t(
                    "stats.carbs",
                )}
            </span>

            <span>
                ${summary.carbs.toFixed(1)}
                /
                ${summary.carbs_goal.toFixed(1)}
                ${grams}
            </span>
        </div>

        <div class="recommendations-summary-meta">
            ${
                calorieRemaining > 0
                    ? nutrition_t(
                        "recommendations.summary.remaining_calories",
                        {
                            value:
                                Math.round(
                                    calorieRemaining,
                                ),
                        },
                    )
                    : nutrition_t(
                        "recommendations.summary.calorie_goal_reached",
                    )
            }

            ${
                proteinRemaining > 0
                    ? ` • ${nutrition_t(
                        "recommendations.summary.remaining_protein",
                        {
                            value:
                                Math.round(
                                    proteinRemaining,
                                ),
                        },
                    )}`
                    : ""
            }
        </div>
    `;
}


export async function loadNutritionRecommendations(): Promise<void> {
    try {
        const data =
            await fetchNutritionRecommendations();

        renderRecommendations(
            data.recommendations,
        );

        renderSummary(
            data.summary,
        );
    } catch (error) {
        console.error(
            "Failed to load nutrition recommendations:",
            error,
        );
    }
}