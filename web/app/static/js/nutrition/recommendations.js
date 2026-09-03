"use strict";
async function fetchNutritionRecommendations() {
    const response = await fetch("/api/nutrition/recommendations");
    if (!response.ok) {
        throw new Error("Failed to fetch nutrition recommendations");
    }
    return response.json();
}
function renderNutritionRecommendations(data) {
    const container = document.querySelector("[data-nutrition-recommendations]");
    if (!container) {
        return;
    }
    container.innerHTML = "";
    for (const recommendation of data.recommendations) {
        const element = document.createElement("div");
        element.className = `nutrition-recommendation nutrition-recommendation--${recommendation.priority}`;
        element.innerHTML = `
      <h3>${recommendation.title}</h3>
      <p>${recommendation.message}</p>
    `;
        container.appendChild(element);
    }
}
async function initNutritionRecommendations() {
    try {
        const data = await fetchNutritionRecommendations();
        renderNutritionRecommendations(data);
    }
    catch (error) {
        console.error("Failed to initialize nutrition recommendations:", error);
    }
}
document.addEventListener("DOMContentLoaded", () => {
    void initNutritionRecommendations();
});
