import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";

export async function loadPlan() {
    try {
        const data = await TrainingAPI.getPlans();
        const plans = data.items || data.plans || data || [];
        trainingStore.plan =
            plans.find(p => p.is_active) ||
            plans[0] ||
            null;
    } catch (_) {
        trainingStore.plan = null;
    }
}
