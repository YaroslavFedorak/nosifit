import json
from pathlib import Path

from flask import request

SUPPORTED_LOCALES = (
    "uk",
    "en",
    "pl",
    "ru",
)

DEFAULT_LOCALE = "uk"
LOCALE_COOKIE = "nosifit_locale"

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"


def resolve_locale() -> str:
    cookie_locale = request.cookies.get(LOCALE_COOKIE)

    if cookie_locale in SUPPORTED_LOCALES:
        return cookie_locale

    browser_locale = request.accept_languages.best_match(SUPPORTED_LOCALES)

    return browser_locale or DEFAULT_LOCALE


def _merge_translations(
    target: dict,
    source: dict,
) -> None:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _merge_translations(
                target[key],
                value,
            )
        else:
            target[key] = value


def _load_translation_directory(
    path: Path,
) -> dict:
    translations: dict = {}

    for file_path in sorted(path.glob("*.json")):
        with file_path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            _merge_translations(
                translations,
                data,
            )

    return translations


def _load_raw_translation(
    locale: str,
    namespace: str,
) -> dict:
    directory = TRANSLATIONS_DIR / locale / namespace

    if directory.is_dir():
        translations = _load_translation_directory(directory)

        if translations:
            return translations

    path = TRANSLATIONS_DIR / locale / f"{namespace}.json"

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:
        data = json.load(file)

    return data if isinstance(data, dict) else {}


def load_translation(
    locale: str,
    namespace: str,
) -> dict:
    """Translations for a namespace with per-key fallback.

    Keys missing in the requested locale fall back to the default locale,
    so a forgotten key shows Ukrainian text instead of a raw key such as
    ``units.kcal``.
    """
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    translations = _load_raw_translation(DEFAULT_LOCALE, namespace)

    if locale != DEFAULT_LOCALE:
        _merge_translations(
            translations,
            _load_raw_translation(locale, namespace),
        )

    return translations


def get_translation(
    locale: str,
    namespace: str,
    key: str,
) -> str:
    translations = load_translation(
        locale,
        namespace,
    )

    value = translations

    for part in key.split("."):
        if not isinstance(value, dict):
            return key

        value = value.get(part)

    if isinstance(value, str):
        return value

    return key
