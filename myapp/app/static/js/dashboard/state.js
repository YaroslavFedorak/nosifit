export const DashboardState = {
    today: null,
    heatmap: [],
    setToday(data) {
        this.today = data;
    },
    setHeatmap(data) {
        this.heatmap = data;
    },
    getToday() {
        return this.today;
    },
    getHeatmap() {
        return this.heatmap;
    }
};
