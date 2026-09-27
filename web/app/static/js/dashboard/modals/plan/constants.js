import { dashboard_t } from "../../../i18n/index.js";
export function getPlanDays() {
    return [
        {
            key: "mon",
            short: dashboard_t("plan.days.mon")
        },
        {
            key: "tue",
            short: dashboard_t("plan.days.tue")
        },
        {
            key: "wed",
            short: dashboard_t("plan.days.wed")
        },
        {
            key: "thu",
            short: dashboard_t("plan.days.thu")
        },
        {
            key: "fri",
            short: dashboard_t("plan.days.fri")
        },
        {
            key: "sat",
            short: dashboard_t("plan.days.sat")
        },
        {
            key: "sun",
            short: dashboard_t("plan.days.sun")
        }
    ];
}
