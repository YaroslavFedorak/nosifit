import { nutrition_t } from "../i18n/index.js";
/** Error thrown by NutritionAPI. `code` comes from the backend (`{error, code}`). */
export class NutritionAPIError extends Error {
    constructor(message, code, status) {
        super(message);
        this.name = "NutritionAPIError";
        this.code = code;
        this.status = status;
    }
}
const KNOWN_CODES = new Set([
    "network",
    "invalid_category",
    "invalid_entry",
    "invalid_product",
    "invalid_water",
    "invalid_weight",
    "meal_not_found",
    "entry_not_found",
    "nothing_to_copy",
    "session_expired",
    "product_not_found",
    "duplicate_product",
    "invalid_barcode",
    "lookup_unavailable",
    "incomplete_product",
    "invalid_product_data",
    "duplicate_barcode",
    "rate_limited",
]);
/** Human, translated text for any error thrown while talking to the API. */
export function describeError(error) {
    if (error instanceof NutritionAPIError && KNOWN_CODES.has(error.code)) {
        return nutrition_t(`errors.${error.code}`);
    }
    return nutrition_t("errors.generic");
}
