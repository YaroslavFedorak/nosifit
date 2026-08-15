export function renderOverview(data) {
    const element = document.getElementById("dashboard-overview");

    if (!element) return;

    element.textContent = data
        ? "Dashboard overview loaded"
        : "No dashboard data";
}
