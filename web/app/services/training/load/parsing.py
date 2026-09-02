def clamp(value, minimum, maximum):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = minimum

    return max(minimum, min(value, maximum))


def parse_int(value, default=0):
    if value is None:
        return default

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    if value is None:
        return default

    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


def parse_reps(value):
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return max(int(value), 0)

    text = str(value).strip()

    if not text:
        return 0

    text = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("/", "-")
        .replace("с", "")
        .replace("s", "")
    )

    if "-" in text:
        parts = text.split("-", 1)

        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return max(int(round((low + high) / 2.0)), 0)
        except (TypeError, ValueError):
            return 0

    try:
        return max(int(float(text.split()[0])), 0)
    except (TypeError, ValueError):
        return 0


def normalize_name(name):
    if not name:
        return ""

    return str(name).strip().lower().replace("_", "-").replace(" ", "-")
