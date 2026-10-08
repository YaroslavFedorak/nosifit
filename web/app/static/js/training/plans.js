import { TrainingAPI } from "./api.js";
import { trainingStore } from "./store.js";
export async function loadPlan() {
    try {
        const data = await TrainingAPI.getPlans();
        const plans = Array.isArray(data)
            ? data
            : data.items ||
                data.plans ||
                [];
        trainingStore.plan =
            plans.find(plan => plan.is_active) ??
                plans[0] ??
                null;
    }
    catch {
        trainingStore.plan = null;
    }
}
