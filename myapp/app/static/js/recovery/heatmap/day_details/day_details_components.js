import { ICONS } from "/static/js/icons/index.js";
import { formatMiniBar, normalizeScore, formatSleep, formatDailySummary } from "../formatters.js";

export function createSummaryCard(title, value, status, score) {
  const card = document.createElement("div");
  card.className = "rc-mini-card";

  const t = document.createElement("div");
  t.className = "rc-mini-title";
  t.textContent = title;

  const row = document.createElement("div");
  row.className = "rc-mini-row";

  const val = document.createElement("div");
  val.className = "rc-mini-value";
  val.textContent = value ?? "—";

  const st = document.createElement("div");
  st.className = "rc-mini-status";
  st.textContent = status ?? "";

  row.appendChild(val);
  row.appendChild(st);

  const bar = document.createElement("div");
  bar.className = "rc-mini-bar";
  const fill = document.createElement("div");
  fill.className = "rc-mini-bar-fill";
  const pct = typeof score === "number" ? Math.max(0, Math.min(100, Math.round(score))) : 0;
  fill.style.width = `${pct}%`;
  bar.appendChild(fill);

  card.appendChild(t);
  card.appendChild(row);
  card.appendChild(bar);

  return card;
}

export function createDailySummary(data) {
  const el = document.createElement("div");
  el.className = "rc-day-daily-summary";
  el.textContent = formatDailySummary(data);
  return el;
}

function safeIcon(name) {
  return ICONS[name] || ICONS["balanced"] || "";
}

export function createHabitRow(h) {
  const row = document.createElement("div");
  row.className = "rc-habit-row";

  const iconWrap = document.createElement("div");
  iconWrap.className = "rc-habit-icon";
  iconWrap.innerHTML = safeIcon(h.icon || h.slug || "droplet");

  const meta = document.createElement("div");
  meta.className = "rc-habit-meta";

  const name = document.createElement("div");
  name.className = "rc-habit-name";
  name.textContent = h.name || h.slug || "—";

  const cat = document.createElement("div");
  cat.className = "rc-habit-category";
  cat.textContent = h.category || "";

  meta.appendChild(name);
  meta.appendChild(cat);

  const status = document.createElement("div");
  status.className = "rc-habit-status";
  status.textContent = h.completed ? "✓" : "○";

  row.appendChild(iconWrap);
  row.appendChild(meta);
  row.appendChild(status);

  return row;
}

export function createRecommendationRow(r) {
  const row = document.createElement("div");
  row.className = "rc-recommendation";

  const icon = document.createElement("div");
  icon.className = "rc-rec-icon";
  const iconName = r.icon || "caution";
  icon.innerHTML = safeIcon(iconName);

  const body = document.createElement("div");
  body.className = "rc-rec-body";

  const text = document.createElement("div");
  text.className = "rc-rec-text";
  text.textContent = r.text || "";

  const sub = document.createElement("div");
  sub.className = "rc-rec-sub";
  sub.textContent = r.priority ? r.priority : "";

  body.appendChild(text);
  body.appendChild(sub);

  row.appendChild(icon);
  row.appendChild(body);

  return row;
}
