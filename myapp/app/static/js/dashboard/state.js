const state = {
    overview: null,
    heatmap: null,
    recommendations: null,
    subscribers: new Map()
};

export function subscribe(key, fn) {
    if (!state.subscribers.has(key)) state.subscribers.set(key, []);
    state.subscribers.get(key).push(fn);
}

function notify(key) {
    const subs = state.subscribers.get(key) || [];
    for (const fn of subs) fn(state[key]);
}

export function setOverview(data) {
    state.overview = data;
    notify("overview");
}

export function setHeatmap(data) {
    state.heatmap = data;
    notify("heatmap");
}

export function setRecommendations(data) {
    state.recommendations = data;
    notify("recommendations");
}

export function getState() {
    return {
        overview: state.overview,
        heatmap: state.heatmap,
        recommendations: state.recommendations
    };
}
