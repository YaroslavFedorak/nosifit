def calculate_quality(ration_items):
    if not ration_items:
        return {
            "whole_foods_percent": 0,
            "processed_foods_percent": 0,
            "fiber": 0,
            "score": 0,
        }

    whole_foods = {
        "овоч",
        "фрукт",
        "круп",
        "рис",
        "греч",
        "вівсян",
        "м'яс",
        "риба",
        "яйц",
        "горіх",
        "бобов",
        "йогурт",
    }

    processed_foods = {
        "печиво",
        "цукер",
        "шокол",
        "ковбас",
        "чіпс",
        "фаст",
        "сосиск",
        "булоч",
        "батонч",
    }

    total_kcal = 0
    whole_kcal = 0
    processed_kcal = 0
    fiber_total = 0

    for item in ration_items:
        name = (item.get("name", "") or "").lower()

        kcal = item.get("calories", 0) or 0

        total_kcal += kcal

        if any(word in name for word in whole_foods):
            whole_kcal += kcal

        if any(word in name for word in processed_foods):
            processed_kcal += kcal

        fiber_total += item.get("fiber", 0) or 0

    if total_kcal <= 0:
        return {
            "whole_foods_percent": 0,
            "processed_foods_percent": 0,
            "fiber": 0,
            "score": 0,
        }

    whole_percent = round(whole_kcal / total_kcal * 100)

    processed_percent = round(processed_kcal / total_kcal * 100)

    fiber_score = min(
        fiber_total / 30 * 100,
        100,
    )

    score = whole_percent * 0.5 + (100 - processed_percent) * 0.2 + fiber_score * 0.3

    return {
        "whole_foods_percent": whole_percent,
        "processed_foods_percent": processed_percent,
        "fiber": round(fiber_total),
        "score": round(score),
    }
