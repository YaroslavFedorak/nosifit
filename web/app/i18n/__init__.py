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
            **params,
        ) -> str:
            value = get_translation(
                locale,
                namespace,
                key,
            )

            for name, replacement in params.items():
                value = value.replace(
                    f"{{{name}}}",
                    str(replacement),
                )

            return value

        def common_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "common",
                key,
                **params,
            )

        def training_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "training",
                key,
                **params,
            )

        def nutrition_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "nutrition",
                key,
                **params,
            )

        return {
            "locale": locale,
            "supported_locales": SUPPORTED_LOCALES,
            "t": common_t,
            "translate": translate,
            "training_t": training_t,
            "nutrition_t": nutrition_t,
        }
