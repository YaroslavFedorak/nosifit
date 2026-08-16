import { DashboardAPI } from "./api.js";

const state = {
    data: null,
    userId: null
};

function resolveUserId() {
    const root = document.getElementById("dashboard-app");
    state.userId = root?.dataset?.userId || null;
    return state.userId;
}

export async function refreshDashboard() {
    const userId = resolveUserId();
    if (!userId) return;

    state.data = await DashboardAPI.getDashboard(userId);
    console.log("Dashboard data:", state.data);
}

export async function initDashboard() {
    await refreshDashboard();
}

export function destroyDashboard() {
    state.data = null;
    state.userId = null;
}
