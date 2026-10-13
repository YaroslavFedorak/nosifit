from flask import request

from shared.i18n import (  # noqa: F401
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS_DIR,
    get_translation,
    load_translation,
)

LOCALE_COOKIE = "nosifit_locale"


def resolve_locale() -> str:
    cookie_locale = request.cookies.get(LOCALE_COOKIE)

    if cookie_locale in SUPPORTED_LOCALES:
        return cookie_locale

    browser_locale = request.accept_languages.best_match(SUPPORTED_LOCALES)

    return browser_locale or DEFAULT_LOCALE
