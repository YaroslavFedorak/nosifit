import { createSummaryCard, createDailySummary, createHabitRow, createRecommendationRow } from "./day_details_components.js";
import { formatSleep } from "../formatters.js";

export function renderDayDetailsBody(container, data) {
  const summaryGrid = document.createElement("div");
  summaryGrid.className = "rc-day-summary-grid";

  const recovery = data.recovery || {};
  const sleep = data.sleep || {};
  const training = data.training || {};
  const habits = data.habits || {};

  summaryGrid.appendChild(createSummaryCard("Відновлення", recovery.score, recovery.status, recovery.energy_score));
  summaryGrid.appendChild(createSummaryCard("Сон", sleep.duration_minutes ? formatSleep(sleep.duration_minutes) : "—", sleep.quality_score ? `${sleep.quality_score}` : "—", sleep.quality_score));
  summaryGrid.appendChild(createSummaryCard("Тренування", training.load ?? "—", `${training.sessions ?? 0} сесій`, training.load));
  summaryGrid.appendChild(createSummaryCard("Звички", `${habits.completed ?? 0} / ${habits.total ?? 0}`, habits.score ?? "—", habits.score));

  const summaryWrap = document.createElement("div");
  summaryWrap.className = "rc-day-details-summary";
  summaryWrap.appendChild(summaryGrid);

  const dailySummary = createDailySummary(data);
  summaryWrap.appendChild(dailySummary);

  container.appendChild(summaryWrap);

  const habitsSection = document.createElement("div");
  habitsSection.className = "rc-day-habits";

  const habitsHeader = document.createElement("div");
  habitsHeader.className = "rc-section-header";
  const title = document.createElement("div");
  title.className = "rc-section-title";
  title.textContent = "Звички";
  const meta = document.createElement("div");
  meta.className = "rc-section-meta";
  meta.textContent = `${habits.completed ?? 0} / ${habits.total ?? 0}`;
  habitsHeader.appendChild(title);
  habitsHeader.appendChild(meta);
  habitsSection.appendChild(habitsHeader);

  const habitsList = document.createElement("div");
  habitsList.id = "rc-habits-list";
  habitsList.className = "rc-habits-list";

  const items = Array.isArray(habits.items) ? habits.items : [];
  const preview = items.slice(0, 5);
  preview.forEach(h => habitsList.appendChild(createHabitRow(h)));

  habitsSection.appendChild(habitsList);

  const habitsFooter = document.createElement("div");
  habitsFooter.className = "rc-habits-footer";
  const toggleBtn = document.createElement("button");
  toggleBtn.id = "rc-habits-toggle";
  toggleBtn.className = "rc-btn rc-btn-sm";
  toggleBtn.textContent = items.length > 5 ? `Показати всі (${items.length})` : "Показати всі";
  habitsFooter.appendChild(toggleBtn);
  habitsSection.appendChild(habitsFooter);

  container.appendChild(habitsSection);

  const recSection = document.createElement("div");
  recSection.className = "rc-day-recommendations";
  const recHeader = document.createElement("div");
  recHeader.className = "rc-section-header";
  const recTitle = document.createElement("div");
  recTitle.className = "rc-section-title";
  recTitle.textContent = "Рекомендації";
  recHeader.appendChild(recTitle);
  recSection.appendChild(recHeader);

  const recList = document.createElement("div");
  recList.id = "rc-recommendations-list";
  recList.className = "rc-recommendations-list";

  const recItems = Array.isArray(data.recommendations?.items) ? data.recommendations.items : [];
  recItems.slice(0, 3).forEach(r => recList.appendChild(createRecommendationRow(r)));

  if ((data.recommendations?.total ?? recItems.length) > 3) {
    const moreBtn = document.createElement("button");
    moreBtn.className = "rc-btn rc-btn-sm";
    moreBtn.textContent = `Показати ще ${(data.recommendations?.total ?? recItems.length) - 3}`;
    moreBtn.addEventListener("click", () => {
      recList.innerHTML = "";
      recItems.forEach(r => recList.appendChild(createRecommendationRow(r)));
      moreBtn.remove();
    });
    recSection.appendChild(recList);
    recSection.appendChild(moreBtn);
  } else {
    recSection.appendChild(recList);
  }

  container.appendChild(recSection);

  toggleBtn.addEventListener("click", () => {
    const list = document.getElementById("rc-habits-list");
    const expanded = list.classList.contains("expanded");
    if (!expanded) {
      list.classList.add("expanded");
      list.innerHTML = "";
      items.forEach(h => list.appendChild(createHabitRow(h)));
      toggleBtn.textContent = "Показати менше";
    } else {
      list.classList.remove("expanded");
      list.innerHTML = "";
      items.slice(0,5).forEach(h => list.appendChild(createHabitRow(h)));
      toggleBtn.textContent = items.length > 5 ? `Показати всі (${items.length})` : "Показати всі";
    }
  });
}
