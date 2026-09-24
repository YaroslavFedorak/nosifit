from flask import g

from .locale import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_translation,
    resolve_locale,
)


def init_i18n(app):

    @app.before_request
    def set_locale():
        g.locale = resolve_locale()

    @app.context_processor
    def inject_i18n():
        locale = getattr(
            g,
            "locale",
            DEFAULT_LOCALE,
        )

        return {
            "locale": locale,
            "supported_locales": SUPPORTED_LOCALES,
            "t": lambda key: get_translation(
                locale,
                key,
            ),
        }
