function safeSet(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


export function renderBalance(data) {
    safeSet(
        "kcal-main-value",
        data.kcal ?? 0
    );

    safeSet(
        "kcal-main-goal",
        `з ${data.kcal_goal ?? 0} ккал`
    );

    safeSet(
        "macro-protein-value",
        `${data.protein ?? 0} / ${data.protein_goal ?? 0} г`
    );

    safeSet(
        "macro-protein-percent",
        `${data.protein_percent ?? 0}%`
    );

    safeSet(
        "macro-fat-value",
        `${data.fat ?? 0} / ${data.fat_goal ?? 0} г`
    );

    safeSet(
        "macro-fat-percent",
        `${data.fat_percent ?? 0}%`
    );

    safeSet(
        "macro-carb-value",
        `${data.carb ?? 0} / ${data.carb_goal ?? 0} г`
    );

    safeSet(
        "macro-carb-percent",
        `${data.carb_percent ?? 0}%`
    );

    safeSet(
        "kcal-balance-label",
        `${data.kcal_balance ?? 0} ккал`
    );

    safeSet(
        "kcal-balance-status",
        data.balance_status ?? "—"
    );

    safeSet(
        "kcal-diff",
        `${data.kcal_diff_label ?? 0} ккал`
    );

    safeSet(
        "protein-diff",
        `${data.protein_diff_label ?? 0} Б`
    );

    safeSet(
        "fat-diff",
        `${data.fat_diff_label ?? 0} Ж`
    );

    safeSet(
        "carb-diff",
        `${data.carb_diff_label ?? 0} В`
    );

    safeSet(
        "water-today",
        `${data.water ?? 0} л`
    );

    safeSet(
        "water-goal",
        `${data.water_goal ?? 0} л`
    );

    if (data.current_weight != null) {
        safeSet(
            "weight-current",
            `${data.current_weight} кг`
        );
    }
}