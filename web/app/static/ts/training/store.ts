import type {
    Exercise,
    WorkoutExercise,
    TrainingPlan,
    RecommendationsData
} from "./api.js";

export type TrainingStore = {
    exercises: Exercise[];
    workout: WorkoutExercise[];
    plan: TrainingPlan | null;
    sessionId: number | string | null;
    currentPlanDay: string;
    recommendations: RecommendationsData | null;
    loading: boolean;
};

declare global {
    interface Window {
        trainingStore: TrainingStore;
    }
}

export const trainingStore: TrainingStore = {
    exercises: [],
    workout: [],
    plan: null,
    sessionId: null,
    currentPlanDay: "mon",
    recommendations: null,
    loading: false
};

window.trainingStore = trainingStore;