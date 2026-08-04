import { RecoveryAPI } from "../api.js";
import { ICONS } from "../../icons/index.js";
import { createDayCard } from "./day_card.js";
import { formatDateLong, formatSleep } from "./formatters.js";

export function openDayDetailsModal(dateStr) {
    const root = document.getElementById("recovery-app");
    if (!root) return;

    const userId = Number(root.dataset.userId || 0);
    if (!userId) return;

    const modal = document.getElementById("rc-day-details-modal");
    const title = document.getElementById("rc-day-details-title");
    const body = document.getElementById("rc-day-details-body");

    if (!modal || !title || !body) return;

    title.textContent = formatDateLong(dateStr);
    body.innerHTML = "";

    RecoveryAPI.getSnapshot(userId, dateStr)
        .then(snapshot => {
            body.innerHTML = "";

            if (!snapshot) {
                const p = document.createElement("p");
                p.textContent = "Немає даних за цей день";
                body.appendChild(p);
            } else {
                const container = document.createElement("div");
                container.className = "rc-day-info";

                container.appendChild(createDayCard({
                    kind: "recovery",
                    label: "Відновлення",
                    score: snapshot.recovery_score,
                    extra: null,
                    icon: ICONS.heart_pulse
                }));

                container.appendChild(createDayCard({
                    kind: "sleep",
                    label: "Сон",
                    score: snapshot.sleep_score,
                    extra: formatSleep(snapshot.sleep_duration_minutes),
                    icon: ICONS.moon
                }));

                container.appendChild(createDayCard({
                    kind: "training",
                    label: "Тренування",
                    score: snapshot.training_score,
                    extra: null,
                    icon: ICONS.exercise
                }));

                container.appendChild(createDayCard({
                    kind: "habits",
                    label: "Звички",
                    score: snapshot.habit_score,
                    extra: null,
                    icon: ICONS.habits
                }));

                container.appendChild(createDayCard({
                    kind: "energy",
                    label: "Енергія",
                    score: snapshot.energy_score,
                    extra: null,
                    icon: ICONS.energy
                }));

                body.appendChild(container);
            }

            modal.classList.add("open");
        })
        .catch(() => {
            body.innerHTML = "";
            const p = document.createElement("p");
            p.textContent = "Не вдалося завантажити дані.";
            body.appendChild(p);
            modal.classList.add("open");
        });
}

export function closeDayDetailsModal() {
    const modal = document.getElementById("rc-day-details-modal");
    if (!modal) return;
    modal.classList.remove("open");
}

export function initDayDetailsModalControls() {
    const buttons = document.querySelectorAll("[data-close-day-details]");
    buttons.forEach(btn => btn.addEventListener("click", closeDayDetailsModal));
}
