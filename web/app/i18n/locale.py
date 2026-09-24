import json
from pathlib import Path

from flask import request

SUPPORTED_LOCALES = ("uk", "en", "pl", "ru")
DEFAULT_LOCALE = "uk"
LOCALE_COOKIE = "nosifit_locale"

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"


def resolve_locale() -> str:
    cookie_locale = request.cookies.get(LOCALE_COOKIE)

    if cookie_locale in SUPPORTED_LOCALES:
        return cookie_locale

    browser_locale = request.accept_languages.best_match(SUPPORTED_LOCALES)

    return browser_locale or DEFAULT_LOCALE


def load_translation(locale: str, namespace: str) -> dict:
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    path = TRANSLATIONS_DIR / locale / f"{namespace}.json"

    if not path.exists():
        path = TRANSLATIONS_DIR / DEFAULT_LOCALE / f"{namespace}.json"

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_translation(locale: str, key: str) -> str:
    namespace, _, path = key.partition(".")

    if not namespace or not path:
        return key

    translations = load_translation(
        locale,
        namespace,
    )

    value = translations

    for part in path.split("."):
        if not isinstance(value, dict):
            return key

        value = value.get(part)

    return value if isinstance(value, str) else key
