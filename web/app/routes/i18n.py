from flask import Blueprint, jsonify

from web.app.i18n.locale import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    load_translation,
)

i18n_bp = Blueprint(
    "i18n",
    __name__,
    url_prefix="/api/i18n",
)


@i18n_bp.get("/<locale>/<namespace>")
def get_translation(locale, namespace):
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    return jsonify(
        load_translation(
            locale,
            namespace,
        )
    )
