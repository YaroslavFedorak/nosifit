import re

from flask import Blueprint, abort, jsonify

from web.app.i18n.locale import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    load_translation,
)

_NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")

i18n_bp = Blueprint(
    "i18n",
    __name__,
    url_prefix="/api/i18n",
)


@i18n_bp.get("/<locale>/<namespace>")
def get_translation(
    locale,
    namespace,
):
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    # The namespace becomes part of a file path.
    if not _NAMESPACE_RE.match(namespace):
        abort(404)

    return jsonify(
        load_translation(
            locale,
            namespace,
        )
    )
