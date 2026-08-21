const state = {
    overview: null,
    heatmap: null,
    recommendations: null,
    training: null,
    subscribers: new Map()
};

export function subscribe(key, fn) {
    if (!state.subscribers.has(key)) {
        state.subscribers.set(key, []);
    }

    state.subscribers.get(key).push(fn);

    return () => {
        const subscribers = state.subscribers.get(key);

        if (!subscribers) {
            return;
        }

        const index = subscribers.indexOf(fn);

        if (index !== -1) {
            subscribers.splice(index, 1);
        }
    };
}

function notify(key) {
    const subscribers = state.subscribers.get(key) || [];

    for (const fn of subscribers) {
        fn(state[key]);
    }
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

export function setTraining(data) {
    state.training = data;
    notify("training");
}

export function getState() {
    return {
        overview: state.overview,
        heatmap: state.heatmap,
        recommendations: state.recommendations,
        training: state.training
    };
}