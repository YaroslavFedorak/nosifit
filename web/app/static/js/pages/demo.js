import { demo_t, getLocale, loadTranslations } from "../i18n/index.js";
import { ICONS } from "../icons/index.js";

const t = (key) => demo_t(key);

const trainingData = [
  { name: "Bench Press", sets: 3, reps: 10, weight: 50, completed: true },
  { name: "Lat Pulldown", sets: 3, reps: 12, weight: 45, completed: true },
  { name: "Shoulder Press", sets: 3, reps: 10, weight: 20, completed: false },
  { name: "Biceps Curl", sets: 3, reps: 12, weight: 12, completed: false },
];

const meals = [
  { name: "Breakfast", calories: 420, protein: 24, fat: 12, carbs: 52, items: ["Oatmeal · 260 kcal", "Banana · 105 kcal", "Greek yogurt · 55 kcal"] },
  { name: "Lunch", calories: 640, protein: 46, fat: 18, carbs: 70, items: ["Chicken · 280 kcal", "Rice · 230 kcal", "Vegetables · 130 kcal"] },
  { name: "Dinner", calories: 510, protein: 34, fat: 16, carbs: 58, items: ["Tuna pasta · 390 kcal", "Salad · 120 kcal"] },
  { name: "Snack", calories: 270, protein: 9, fat: 14, carbs: 25, items: ["Fruit · 120 kcal", "Nuts · 150 kcal"] },
];

const habits = [
  { name: "Sleep on schedule", category: "sleep", reason: "Supports consistent recovery", points: 10, icon: "bed", completed: true },
  { name: "Enough water", category: "hydration", reason: "Supports hydration through the day", points: 8, icon: "droplet", completed: true },
  { name: "Light mobility", category: "activity", reason: "Keeps movement comfortable", points: 6, icon: "walk", completed: true },
  { name: "Recovery session", category: "recovery", reason: "Creates space for recovery", points: 10, icon: "rest", completed: true },
  { name: "Screen-free rest", category: "stress", reason: "Helps reduce evening stimulation", points: 7, icon: "breathing", completed: false },
];

const monthNames = [
  ["heatmap.months.january", "Jan"], ["heatmap.months.february", "Feb"],
  ["heatmap.months.march", "Mar"], ["heatmap.months.april", "Apr"],
  ["heatmap.months.may", "May"], ["heatmap.months.june", "Jun"],
  ["heatmap.months.july", "Jul"], ["heatmap.months.august", "Aug"],
  ["heatmap.months.september", "Sep"], ["heatmap.months.october", "Oct"],
  ["heatmap.months.november", "Nov"], ["heatmap.months.december", "Dec"],
];

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    const value = t(key);
    if (value !== key) element.textContent = value;
  });
}

function createInput(exercise, value, label) {
  const wrap = document.createElement("div");
  wrap.className = "db-input-inline";
  const input = document.createElement("input");
  input.className = "db-input-field";
  input.type = "text";
  input.value = value;
  input.disabled = exercise.completed;
  input.setAttribute("aria-label", label);
  const text = document.createElement("span");
  text.className = "db-input-inline-label";
  text.textContent = label;
  wrap.append(input, text);
  return wrap;
}

function updateTrainingProgress() {
  const completed = trainingData.filter((item) => item.completed).length;
  const percent = Math.round((completed / trainingData.length) * 100);
  document.getElementById("demo-training-progress").textContent = percent + "%";
  document.getElementById("demo-training-progress-bar").style.width = percent + "%";
}

function renderTraining() {
  const container = document.getElementById("demo-training-list");
  if (!container) return;
  container.innerHTML = "";

  trainingData.forEach((exercise) => {
    const row = document.createElement("div");
    row.className = "db-session-ex-row" + (exercise.completed ? " db-ex-done" : "");

    const name = document.createElement("div");
    name.className = "db-session-ex-name-wrap";
    const nameText = document.createElement("div");
    nameText.className = "db-session-ex-name";
    nameText.textContent = exercise.name;
    name.appendChild(nameText);

    const sets = createInput(exercise, exercise.sets, "sets");
    const reps = createInput(exercise, exercise.reps, "reps");
    const weight = createInput(exercise, exercise.weight + " kg", "load");

    const check = document.createElement("button");
    check.type = "button";
    check.className = "db-ex-check" + (exercise.completed ? " checked" : "");
    check.setAttribute("aria-label", "Toggle exercise");
    check.addEventListener("click", () => {
      exercise.completed = !exercise.completed;
      renderTraining();
    });

    row.append(name, sets, reps, weight, check);
    container.appendChild(row);
  });

  updateTrainingProgress();
}

function createMealCard(meal) {
  const card = document.createElement("article");
  card.className = "meal-card-large";

  const header = document.createElement("div");
  header.className = "meal-header-large";

  const info = document.createElement("button");
  info.type = "button";
  info.className = "meal-title-block";

  const titleRow = document.createElement("div");
  titleRow.className = "meal-title-row";

  const title = document.createElement("span");
  title.className = "meal-title";
  title.textContent = meal.name;

  const icon = document.createElement("span");
  icon.className = "meal-expand-icon";
  icon.textContent = "⌄";

  titleRow.append(title, icon);

  const meta = document.createElement("div");
  meta.className = "meal-meta-large";
  meta.textContent = meal.calories + " kcal · P " + meal.protein + " · F " + meal.fat + " · C " + meal.carbs;

  info.append(titleRow, meta);

  const content = document.createElement("div");
  content.className = "meal-content-large";
  const items = document.createElement("div");
  items.className = "meal-items-large";

  meal.items.forEach((value) => {
    const row = document.createElement("div");
    row.className = "meal-item-row-large";
    const name = document.createElement("div");
    name.className = "meal-item-name-large";
    name.textContent = value;
    row.appendChild(name);
    items.appendChild(row);
  });

  content.appendChild(items);
  info.addEventListener("click", () => card.classList.toggle("meal-expanded"));
  header.appendChild(info);
  card.append(header, content);
  return card;
}

function renderMeals() {
  const list = document.getElementById("demo-meals-list");
  if (!list) return;
  list.innerHTML = "";
  meals.forEach((meal) => list.appendChild(createMealCard(meal)));
}

function createHabitItem(habit) {
  const item = document.createElement("div");
  item.className = "habit-item habit-user " + (habit.completed ? "habit-completed " : "") + "habit-cat-" + habit.category;

  const main = document.createElement("div");
  main.className = "habit-main";

  const icon = document.createElement("div");
  icon.className = "habit-icon";
  icon.innerHTML = ICONS[habit.icon] ?? ICONS.rest;

  const text = document.createElement("div");
  text.className = "habit-text";

  const title = document.createElement("div");
  title.className = "habit-title";
  title.textContent = habit.name;

  const meta = document.createElement("div");
  meta.className = "habit-meta-row";

  const category = document.createElement("div");
  category.className = "habit-category-badge";
  category.textContent = habit.category;

  const reason = document.createElement("div");
  reason.className = "habit-reason";
  reason.textContent = habit.reason;

  meta.appendChild(category);
  text.append(title, meta, reason);
  main.append(icon, text);

  const actions = document.createElement("div");
  actions.className = "habit-actions";

  const impact = document.createElement("div");
  impact.className = "habit-recovery-impact";
  impact.textContent = "Recovery +" + habit.points;

  const check = document.createElement("button");
  check.type = "button";
  check.className = "habit-check" + (habit.completed ? " habit-check-completed" : "");
  check.setAttribute("aria-label", "Toggle habit");
  check.addEventListener("click", () => {
    habit.completed = !habit.completed;
    item.classList.toggle("habit-completed");
    check.classList.toggle("habit-check-completed");
  });

  actions.append(impact, check);
  item.append(main, actions);
  return item;
}

function renderHabits() {
  const list = document.getElementById("demo-habits-list");
  if (!list) return;
  list.innerHTML = "";
  habits.forEach((habit) => list.appendChild(createHabitItem(habit)));
}

function renderHeatmap() {
  const container = document.getElementById("demo-heatmap");
  const months = document.getElementById("demo-heatmap-months");
  if (!container || !months) return;

  months.innerHTML = "";
  monthNames.forEach(([key, fallback]) => {
    const label = document.createElement("span");
    const value = t(key);
    label.textContent = value === key ? fallback : value;
    months.appendChild(label);
  });

  container.innerHTML = "";
  const year = new Date().getFullYear();
  const today = new Date();

  for (let day = 0; day < 365; day += 1) {
    const date = new Date(year, 0, day + 1);
    const level = (day * 7 + date.getDate()) % 7;
    const cell = document.createElement("div");

    cell.className = "heatmap-cell";
    cell.dataset.level = String(level);

    if (date.toDateString() === today.toDateString()) cell.classList.add("today");

    const tooltip = document.createElement("div");
    tooltip.className = "heatmap-tooltip";

    const dateText = document.createElement("strong");
    dateText.textContent = date.toLocaleDateString(getLocale(), { day: "numeric", month: "long" });

    const balance = document.createElement("span");
    balance.textContent = "Balance " + Math.max(58, 60 + level * 6);

    const training = document.createElement("span");
    training.textContent = "Training " + Math.max(48, 55 + level * 5);

    const recovery = document.createElement("span");
    recovery.textContent = "Recovery " + Math.max(52, 58 + level * 4);

    tooltip.append(dateText, balance, training, recovery);
    cell.appendChild(tooltip);
    container.appendChild(cell);
  }
}

async function init() {
  try {
    await loadTranslations("demo");
    document.documentElement.lang = getLocale();
    applyTranslations();
    renderHeatmap();
    renderTraining();
    renderMeals();
    renderHabits();
  } catch (error) {
    console.error("Failed to load demo:", error);
  }
}

init();
