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

        def translate(
            namespace: str,
            key: str,
        ) -> str:
            return get_translation(
                locale,
                namespace,
                key,
            )

        return {
            "locale": locale,
            "supported_locales": SUPPORTED_LOCALES,
            "t": lambda key: translate(
                "common",
                key,
            ),
            "translate": translate,
            "training_t": lambda key: translate(
                "training",
                key,
            ),
        }
