def calculate_daily_score(training_score, nutrition_score, recovery_score):
    values = []
    for v in (training_score, nutrition_score, recovery_score):
        if v is None:
            continue
        try:
            values.append(float(v))
        except Exception:
            continue
    if not values:
        return 0
    return int(round(sum(values) / len(values)))
