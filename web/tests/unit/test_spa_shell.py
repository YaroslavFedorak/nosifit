"""The /app shell: who may open which page, and what it hands to the React bundle."""

import json
import re

PASSWORD = "password123"


def _login(client, user):
    response = client.post("/auth/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code in (302, 303)


def _bootstrap(response):
    html = response.get_data(as_text=True)
    match = re.search(r'<script id="nosi-bootstrap" type="application/json">(.*?)</script>', html, re.S)
    assert match, "the shell must carry its bootstrap data"
    return json.loads(match.group(1))


def test_public_pages_render_the_shell_for_visitors(client):
    for path in ("/app/welcome", "/app/how-it-works"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert b'<div id="root"></div>' in response.data
        assert _bootstrap(response)["user"] is None


def test_user_pages_send_visitors_to_sign_in(client):
    for path in ("/app/dashboard", "/app/training", "/app/nutrition", "/app/recovery"):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/auth/login" in response.headers["Location"]


def test_signed_in_user_gets_the_shell_with_their_name(client, user):
    _login(client, user)
    response = client.get("/app/training")
    assert response.status_code == 200
    data = _bootstrap(response)
    assert data["user"] == {"id": user.id, "name": user.username}
    assert data["locale"] in {"en", "uk", "pl", "ru"}


def test_app_root_goes_to_the_right_first_page(client, user):
    assert client.get("/app/").headers["Location"].endswith("/app/welcome")
    _login(client, user)
    assert client.get("/app/").headers["Location"].endswith("/app/dashboard")


def test_unknown_pages_are_not_served(client):
    for path in ("/app/nope", "/app/dashboard/extra", "/app/../profile"):
        assert client.get(path).status_code == 404, path


def test_shell_loads_the_versioned_bundle(app, client):
    version = app.config["ASSET_VERSION"]
    html = client.get("/app/welcome").get_data(as_text=True)
    assert f"/static/{version}/app/assets/app.js" in html
    assert f"/static/{version}/app/assets/app.css" in html


def test_profile_and_settings_are_user_pages(client, user):
    for path in ("/app/profile", "/app/settings"):
        assert client.get(path).status_code == 302, path
    _login(client, user)
    for path in ("/app/profile", "/app/settings"):
        assert client.get(path).status_code == 200, path


def test_shell_tells_the_interface_what_the_account_may_use(client, user):
    assert _bootstrap(client.get("/app/welcome"))["features"] == {}
    _login(client, user)
    assert _bootstrap(client.get("/app/dashboard"))["features"] == {"plan_generation": bool(user.is_premium)}


def test_signed_in_pages_allow_the_barcode_scanner(client, user):
    """The food picker opens from every signed-in page; public pages keep the camera off."""
    assert "camera=()" in client.get("/app/welcome").headers["Permissions-Policy"]
    _login(client, user)
    response = client.get("/app/recovery")
    assert "camera=(self)" in response.headers["Permissions-Policy"]
    assert "'wasm-unsafe-eval'" in response.headers["Content-Security-Policy"]


def _preloaded(html):
    return re.findall(r'<link rel="modulepreload" href="/static/[0-9a-f]+/app/(assets/[^"]+)"', html)


def test_shell_asks_for_the_page_code_together_with_the_bundle(app, client, user):
    """The page's chunks and its language are preloaded, so the browser does
    not find them one round trip after another (web/app/routes/spa/bundle.py)."""
    from pathlib import Path

    from web.app.routes.spa.bundle import _manifest

    manifest = _manifest(app.static_folder, app.config["ASSET_VERSION"])
    assert manifest, "npm --prefix frontend run build writes .vite/manifest.json"

    _login(client, user)
    for page, module in (("dashboard", "src/pages/Dashboard.tsx"), ("training", "src/pages/Training.tsx")):
        html = client.get(f"/app/{page}", headers={"Accept-Language": "uk"}).get_data(as_text=True)
        files = _preloaded(html)
        assert manifest[module]["file"] in files, page
        assert manifest["src/i18n/uk.ts"]["file"] in files
        assert manifest["src/i18n/en.ts"]["file"] not in files
        # The entry is loaded by its <script>, and every listed file exists.
        assert "assets/app.js" not in files
        assert all((Path(app.static_folder) / "app" / name).is_file() for name in files)
        assert len(files) == len(set(files))


def test_shell_hands_the_interface_the_version_of_the_server_texts(client):
    from shared.i18n import translations_version

    assert _bootstrap(client.get("/app/welcome"))["text_version"] == translations_version()


def test_shell_works_without_a_manifest(app, client, monkeypatch):
    from web.app.routes.spa import bundle

    monkeypatch.setattr(bundle, "MANIFEST", "missing/manifest.json")
    bundle._manifest.cache_clear()
    try:
        response = client.get("/app/welcome")
        assert response.status_code == 200
        assert _preloaded(response.get_data(as_text=True)) == []
    finally:
        bundle._manifest.cache_clear()


def test_every_page_has_its_module_listed():
    """A page missing from PAGE_MODULES would still work, only load slower."""
    from pathlib import Path

    from web.app.routes.spa.bundle import PAGE_MODULES
    from web.app.routes.spa.pages import PUBLIC_PAGES, USER_PAGES

    assert set(PAGE_MODULES) == PUBLIC_PAGES | USER_PAGES
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    app_routes = (frontend / "src" / "App.tsx").read_text(encoding="utf-8")
    for module in PAGE_MODULES.values():
        assert (frontend / module).is_file(), module
        assert f'import("./{module.removeprefix("src/").removesuffix(".tsx")}")' in app_routes, module


def test_shell_hands_the_interface_the_app_version(client):
    from shared.version import app_version, release_stage

    data = _bootstrap(client.get("/app/welcome"))
    assert data["version"] == app_version()
    assert data["stage"] == release_stage()
