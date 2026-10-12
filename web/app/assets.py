"""Static asset caching.

Static files are served under ``/static/<version>/...`` where ``version`` is a
hash of every file in the static folder. ``url_for('static', ...)`` builds
these URLs, and relative references inside the files (CSS ``@import``, JS
``import "./x.js"``) resolve under the same versioned prefix, so browsers can
cache all of them for a year without asking the server again. Any change to
any static file changes the version, so a deploy never serves stale assets.

Plain ``/static/...`` URLs (the web manifest, the barcode vendor path, links
from an older deploy) keep working with revalidation on every use.
"""

import hashlib
import os
import re

from flask import request, send_from_directory

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Versioned URLs never change content: cache for a year, skip revalidation.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
REVALIDATE_CACHE = "no-cache"

_VERSION_SEGMENT = re.compile(r"^[0-9a-f]{12}/")


def compute_asset_version(static_dir: str = STATIC_DIR) -> str:
    """Hash of the static folder's file names and contents.

    Deterministic, so every gunicorn worker and instance agrees on it.
    """
    digest = hashlib.sha256()
    for root, dirs, files in os.walk(static_dir):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            digest.update(os.path.relpath(path, static_dir).encode())
            digest.update(b"\0")
            with open(path, "rb") as fh:
                digest.update(fh.read())
            digest.update(b"\0")
    return digest.hexdigest()[:12]


def init_assets(app, version: str) -> None:
    app.config["ASSET_VERSION"] = version
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000

    @app.get("/static/<path:filename>", endpoint="static_unversioned")
    def static_unversioned(filename):
        # A URL from a previous deploy: serve the current file, uncached.
        filename = _VERSION_SEGMENT.sub("", filename, count=1)
        response = send_from_directory(app.static_folder, filename)
        response.headers["Cache-Control"] = REVALIDATE_CACHE
        return response

    @app.after_request
    def _immutable_static(response):
        if response.status_code == 200 and app.static_url_path and (
            request.path.startswith(app.static_url_path + "/")
        ):
            response.headers["Cache-Control"] = IMMUTABLE_CACHE
        return response
