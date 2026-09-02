const MINI_BAR_SEGMENTS = 5;
export const LOW_THRESHOLD = 40;
export const HIGH_THRESHOLD = 70;

const MONTH_SHORT_UA = ["січ","лют","бер","квіт","трав","черв","лип","серп","вер","жовт","лист","груд"];
const WEEKDAY_UA = ["Неділя","Понеділок","Вівторок","Середа","Четвер","П'ятниця","Субота"];

export function normalizeScore(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(Math.round(value), 100));
}

export function formatScore(value) {
  return value == null ? 0 : normalizeScore(value);
}

export function getLevel(value) {
  const v = normalizeScore(value);
  if (v < LOW_THRESHOLD) return "low";
  if (v < HIGH_THRESHOLD) return "medium";
  return "high";
}

export function formatMiniBar(value) {
  const v = normalizeScore(value);
  const blocks = Math.round(v / (100 / MINI_BAR_SEGMENTS));
  return "▰".repeat(blocks) + "▱".repeat(MINI_BAR_SEGMENTS - blocks);
}

export function formatDateShort(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const day = d.getDate();
  const month = MONTH_SHORT_UA[d.getMonth()] || "";
  return `${day} ${month}`;
}

export function formatDateLong(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("uk-UA", { day: "numeric", month: "long", year: "numeric" });
}

export function formatWeekday(dateStr) {
  const d = new Date(dateStr);
  return WEEKDAY_UA[d.getDay()] || "";
}

export function formatSleep(minutes) {
  if (minutes == null) return null;
  const total = Number(minutes);
  if (Number.isNaN(total) || total < 0) return null;
  const h = Math.floor(total / 60);
  const m = String(total % 60).padStart(2, "0");
  return `${h} год ${m} хв`;
}

export function formatTooltipDayHTML(data) {
  const date = data?.date ? formatDateShort(data.date) : "";
  const score = data?.recovery_score != null ? normalizeScore(data.recovery_score) : 0;
  return `<div class="tt-single-line"><span class="tt-score">${score} відновлення</span><span class="tt-date">${date}</span></div>`;
}

export function formatDailySummary(data) {
  const trainingCount = data.training?.sessions ?? 0;
  const sleepText = data.sleep?.duration_minutes ? formatSleep(data.sleep.duration_minutes) : null;
  const habitsText = `${data.habits?.completed ?? 0}/${data.habits?.total ?? 0}`;
  const parts = [];
  if (trainingCount) parts.push(`Тренування: ${trainingCount} сесій`);
  if (sleepText) parts.push(`Сон: ${sleepText}`);
  parts.push(`Звички: ${habitsText} виконано`);
  return parts.join(" · ");
}
