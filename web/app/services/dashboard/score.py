def calculate_daily_score(training_score, nutrition_score, recovery_score):
    values = []

    for value in (training_score, nutrition_score, recovery_score):
        if value is None:
            continue

        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    if not values:
        return 0

    return int(round(sum(values) / len(values)))
