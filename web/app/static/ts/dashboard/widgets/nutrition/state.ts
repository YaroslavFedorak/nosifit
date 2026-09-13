import type {
    NutritionDay,
} from "../../../nutrition/types.js";


let nutritionDay: NutritionDay | null = null;


export function setNutritionDay(
    data: NutritionDay,
): void {
    nutritionDay = data;
}


export function getNutritionDay(): NutritionDay | null {
    return nutritionDay;
}