import re

from flask import Blueprint, abort, jsonify, request

from shared.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    load_translation,
    translations_version,
)

# The texts are the same for everyone and change only with a deploy. A URL
# carrying the current version (``?v=``, as the React pages request it) may
# stay in any cache for a year; any other URL is revalidated as before.
VERSIONED_CACHE = "public, max-age=31536000, immutable"

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

    response = jsonify(
        load_translation(
            locale,
            namespace,
        )
    )
    if request.args.get("v") == translations_version():
        response.headers["Cache-Control"] = VERSIONED_CACHE
    return response
