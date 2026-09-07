async function fetchNutritionRecommendations() {
    const response = await fetch("/api/nutrition/recommendations", {
        credentials: "same-origin",
    });
    if (!response.ok) {
        throw new Error("Failed to fetch nutrition recommendations");
    }
    return response.json();
}
function getPriorityClass(priority) {
    return `recommendation-item--${priority}`;
}
function renderRecommendation(recommendation) {
    const element = document.createElement("div");
    element.className = [
        "recommendation-item",
        getPriorityClass(recommendation.priority),
    ].join(" ");
    element.innerHTML = `
    <div class="recommendation-marker"></div>

    <div class="recommendation-content">
      <div class="recommendation-title">
        ${recommendation.title}
      </div>

      <div class="recommendation-text">
        ${recommendation.message}
      </div>
    </div>
  `;
    return element;
}
function renderEmptyRecommendations(container) {
    container.innerHTML = `
    <div class="recommendation-item recommendation-item--low">
      <div class="recommendation-marker"></div>

      <div class="recommendation-content">
        <div class="recommendation-title">
          Раціон виглядає збалансовано
        </div>

        <div class="recommendation-text">
          На цей момент немає критичних рекомендацій.
          Продовжуйте стежити за харчуванням протягом дня.
        </div>
      </div>
    </div>
  `;
}
function renderRecommendations(recommendations) {
    const container = document.querySelector("[data-nutrition-recommendations]");
    if (!container) {
        return;
    }
    container.innerHTML = "";
    if (recommendations.length === 0) {
        renderEmptyRecommendations(container);
        return;
    }
    for (const recommendation of recommendations) {
        container.appendChild(renderRecommendation(recommendation));
    }
}
function renderSummary(summary) {
    const container = document.querySelector("[data-nutrition-recommendations-summary]");
    if (!container) {
        return;
    }
    const calorieRemaining = Math.max(summary.calories_goal - summary.calories, 0);
    const proteinRemaining = Math.max(summary.protein_goal - summary.protein, 0);
    container.innerHTML = `
    <div class="recommendations-summary-row">
      <span>Калорії</span>
      <span>
        ${Math.round(summary.calories)}
        / ${Math.round(summary.calories_goal)} ккал
      </span>
    </div>

    <div class="recommendations-summary-row">
      <span>Білок</span>
      <span>
        ${summary.protein.toFixed(1)}
        / ${summary.protein_goal.toFixed(1)} г
      </span>
    </div>

    <div class="recommendations-summary-row">
      <span>Жири</span>
      <span>
        ${summary.fat.toFixed(1)}
        / ${summary.fat_goal.toFixed(1)} г
      </span>
    </div>

    <div class="recommendations-summary-row">
      <span>Вуглеводи</span>
      <span>
        ${summary.carbs.toFixed(1)}
        / ${summary.carbs_goal.toFixed(1)} г
      </span>
    </div>

    <div class="recommendations-summary-meta">
      ${calorieRemaining > 0
        ? `Залишилось близько ${Math.round(calorieRemaining)} ккал`
        : "Ціль по калоріях досягнута"}

      ${proteinRemaining > 0
        ? ` • ${Math.round(proteinRemaining)} г білка`
        : ""}
    </div>
  `;
}
export async function loadNutritionRecommendations() {
    try {
        const data = await fetchNutritionRecommendations();
        renderRecommendations(data.recommendations);
        renderSummary(data.summary);
    }
    catch (error) {
        console.error("Failed to load nutrition recommendations:", error);
    }
}
