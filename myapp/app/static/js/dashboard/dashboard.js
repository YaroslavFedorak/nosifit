import { DashboardAPI } from "./api.js";
import { DashboardState } from "./state.js";
import { renderDailyScore } from "./widgets/daily_score.js";
import { renderCheckin } from "./widgets/checkin.js";
import { renderCategories } from "./widgets/categories.js";
import { renderHeatmap } from "./heatmap/render.js";
import { openDayModal } from "./heatmap/modal.js";

export async function initDashboard() {
    const todayEl = document.getElementById("nf-daily-score");
    const checkinEl = document.getElementById("nf-checkin");
    const categoriesEl = document.getElementById("nf-categories");
    const heatmapEl = document.getElementById("nf-heatmap");

    try {
        const today = await DashboardAPI.today();
        DashboardState.setToday(today);
        renderDailyScore(todayEl, today);
        renderCheckin(checkinEl, today);
        renderCategories(categoriesEl, today);
    } catch (e) {
        console.error(e);
    }

    try {
        const heatmap = await DashboardAPI.heatmap();
        DashboardState.setHeatmap(heatmap);
        renderHeatmap(heatmapEl, heatmap);
    } catch (e) {
        console.error(e);
    }

    window.addEventListener("dashboard:dayclick", async (ev) => {
        const date = ev.detail.date;
        try {
            const data = await DashboardAPI.day(date);
            openDayModal(data);
        } catch (e) {
            console.error(e);
        }
    });
}
