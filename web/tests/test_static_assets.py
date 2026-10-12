from pathlib import Path

import brotli
from flask import url_for

from web.app.assets import IMMUTABLE_CACHE, REVALIDATE_CACHE, STATIC_DIR as _STATIC_DIR

STATIC_DIR = Path(_STATIC_DIR)


def test_static_urls_carry_the_asset_version(app):
    with app.test_request_context():
        url = url_for("static", filename="css/core/reset.css")
    assert url == f"/static/{app.config['ASSET_VERSION']}/css/core/reset.css"


def test_versioned_static_files_are_cached_long_term(app, client):
    version = app.config["ASSET_VERSION"]
    response = client.get(f"/static/{version}/css/core/reset.css")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == IMMUTABLE_CACHE


def test_relative_module_imports_stay_versioned(app, client):
    # nav.js imports "./scroll-end.js"; it resolves under the same prefix.
    version = app.config["ASSET_VERSION"]
    response = client.get(f"/static/{version}/js/core/scroll-end.js")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == IMMUTABLE_CACHE


def test_unversioned_and_stale_static_urls_still_work_uncached(client):
    for path in (
        "/static/site.webmanifest",
        "/static/0123456789ab/css/core/reset.css",  # an older deploy's version
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["Cache-Control"] == REVALIDATE_CACHE


def test_missing_static_file_is_not_cached(app, client):
    version = app.config["ASSET_VERSION"]
    response = client.get(f"/static/{version}/css/missing.css")
    assert response.status_code == 404
    assert response.headers.get("Cache-Control") != IMMUTABLE_CACHE


def test_text_assets_are_compressed(app, client):
    version = app.config["ASSET_VERSION"]
    response = client.get(
        f"/static/{version}/css/core/layout.css",
        headers={"Accept-Encoding": "gzip, deflate, br"},
    )
    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "br"
    original = (STATIC_DIR / "css" / "core" / "layout.css").read_bytes()
    assert brotli.decompress(response.get_data()) == original
    assert len(response.get_data()) < len(original)
    assert "Accept-Encoding" in response.headers["Vary"]


def test_pages_reference_versioned_assets(app, client):
    page = client.get("/auth/register")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert f"/static/{app.config['ASSET_VERSION']}/css/auth/register.css" in html
    assert 'href="/static/css/' not in html
