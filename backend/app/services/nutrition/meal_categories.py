"""Canonical meal categories.

Meals are stored with a language-independent key (``breakfast``, ``lunch``,
``dinner``, ``snack``). Clients translate the key for display. Older clients
and historical rows used localized labels such as ``"Сніданок"``; those are
accepted as aliases so nothing breaks while clients migrate.
"""

MEAL_CATEGORIES = ("breakfast", "lunch", "dinner", "snack")

DEFAULT_MEAL_CATEGORY = "snack"

_ALIASES = {
    "breakfast": ("breakfast", "сніданок", "śniadanie", "sniadanie", "завтрак"),
    "lunch": ("lunch", "обід", "obiad", "обед"),
    "dinner": ("dinner", "вечеря", "kolacja", "ужин"),
    "snack": ("snack", "перекус", "przekąska", "przekaska"),
}

_LOOKUP = {
    alias: key
    for key, aliases in _ALIASES.items()
    for alias in aliases
}


def normalize_meal_category(value):
    """Return the canonical key for a category value, or ``None``."""
    if value is None:
        return None

    normalized = str(value).strip().lower()

    if not normalized:
        return None

    return _LOOKUP.get(normalized)


def legacy_aliases():
    """All (alias, key) pairs. Used by the data migration."""
    return sorted(_LOOKUP.items())
