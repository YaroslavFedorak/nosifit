type StateKey =
    | "overview"
    | "heatmap"
    | "recommendations"
    | "training";

type Subscriber = (data: any) => void;

interface DashboardState {
    overview: any;
    heatmap: any;
    recommendations: any;
    training: any;
    subscribers: Map<StateKey, Subscriber[]>;
}

const state: DashboardState = {
    overview: null,
    heatmap: null,
    recommendations: null,
    training: null,
    subscribers: new Map()
};

export function subscribe(
    key: StateKey,
    fn: Subscriber
): () => void {
    if (!state.subscribers.has(key)) {
        state.subscribers.set(key, []);
    }

    const subscribers = state.subscribers.get(key)!;

    subscribers.push(fn);

    return () => {
        const index = subscribers.indexOf(fn);

        if (index !== -1) {
            subscribers.splice(index, 1);
        }
    };
}

function notify(key: StateKey): void {
    const subscribers =
        state.subscribers.get(key) || [];

    for (const fn of subscribers) {
        try {
            fn(state[key]);
        } catch (error) {
            console.error(
                `Dashboard state subscriber error: ${key}`,
                error
            );
        }
    }
}

export function setOverview(data: any): void {
    state.overview = data;
    notify("overview");
}

export function setHeatmap(data: any): void {
    state.heatmap = data;
    notify("heatmap");
}

export function setRecommendations(data: any): void {
    state.recommendations = data;
    notify("recommendations");
}

export function setTraining(data: any): void {
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