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
