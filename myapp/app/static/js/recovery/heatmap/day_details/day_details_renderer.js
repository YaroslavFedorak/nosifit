import { createSummaryCard, createDailySummary, createHabitsGrid, createHabitRow, createRecommendationRow } from "./day_details_components.js";
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

  const itemsRaw = Array.isArray(habits.items) ? habits.items : [];
  const items = itemsRaw.filter(h => !!h.user_habit_id);

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

  const previewCount = 8;
  const previewItems = items.slice(0, previewCount);
  const grid = createHabitsGrid(items, previewCount);
  habitsList.appendChild(grid);

  habitsSection.appendChild(habitsList);

  const habitsFooter = document.createElement("div");
  habitsFooter.className = "rc-habits-footer";
  const toggleBtn = document.createElement("button");
  toggleBtn.id = "rc-habits-toggle";
  toggleBtn.className = "rc-btn rc-btn-sm";
  toggleBtn.textContent = items.length > previewCount ? `Показати всі (${items.length})` : "Показати всі";
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

  const recGrid = document.createElement("div");
  recGrid.className = "rc-recommendations-grid";
  const recLeft = document.createElement("div");
  recLeft.className = "rc-recommendations-col";
  const recRight = document.createElement("div");
  recRight.className = "rc-recommendations-col";

  const recPreview = recItems.slice(0, 6);
  recPreview.forEach((r, i) => {
    const col = i % 2 === 0 ? recLeft : recRight;
    col.appendChild(createRecommendationRow(r));
  });

  recGrid.appendChild(recLeft);
  recGrid.appendChild(recRight);
  recList.appendChild(recGrid);

  recSection.appendChild(recList);

  if ((data.recommendations?.total ?? recItems.length) > 6) {
    const moreBtn = document.createElement("button");
    moreBtn.className = "rc-btn rc-btn-sm";
    moreBtn.textContent = `Показати ще ${(data.recommendations?.total ?? recItems.length) - 6}`;
    moreBtn.addEventListener("click", () => {
      recList.innerHTML = "";
      const fullGrid = document.createElement("div");
      fullGrid.className = "rc-recommendations-grid";
      const left = document.createElement("div");
      left.className = "rc-recommendations-col";
      const right = document.createElement("div");
      right.className = "rc-recommendations-col";
      recItems.forEach((r, i) => {
        const col = i % 2 === 0 ? left : right;
        col.appendChild(createRecommendationRow(r));
      });
      fullGrid.appendChild(left);
      fullGrid.appendChild(right);
      recList.appendChild(fullGrid);
      moreBtn.remove();
    });
    recSection.appendChild(moreBtn);
  }

  container.appendChild(recSection);

  toggleBtn.addEventListener("click", () => {
    const list = document.getElementById("rc-habits-list");
    const expanded = list.classList.contains("expanded");
    if (!expanded) {
      list.classList.add("expanded");
      list.innerHTML = "";
      const fullGrid = document.createElement("div");
      fullGrid.className = "rc-habits-grid";
      const leftCol = document.createElement("div");
      leftCol.className = "rc-habits-col";
      const rightCol = document.createElement("div");
      rightCol.className = "rc-habits-col";
      items.forEach((h, i) => {
        const col = i % 2 === 0 ? leftCol : rightCol;
        col.appendChild(createHabitRow(h));
      });
      fullGrid.appendChild(leftCol);
      fullGrid.appendChild(rightCol);
      list.appendChild(fullGrid);
      toggleBtn.textContent = "Показати менше";
    } else {
      list.classList.remove("expanded");
      list.innerHTML = "";
      const smallGrid = createHabitsGrid(items, previewCount);
      list.appendChild(smallGrid);
      toggleBtn.textContent = items.length > previewCount ? `Показати всі (${items.length})` : "Показати всі";
    }
  });
}
