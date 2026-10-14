"""The Telegram bot's own HTTP clients against the real web app.

TelegramAuthClient and NosiFitAPI run unchanged; a requests transport
adapter hands their requests to the Flask app instead of the network. This
pins down what the bot sees for each error the API answers.
"""

from http.cookies import SimpleCookie
from urllib.parse import urlsplit

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from backend.app.extensions import db
from backend.app.models.telegram import TelegramIdentity
from telegram_bot.services import telegram_auth as bot_auth
from telegram_bot.services.api import ERROR_MESSAGES, NosiFitAPI, NosiFitAPIError
from telegram_bot.services.telegram_auth import TelegramAuthClient, TelegramUser

SECRET = "bot-client-contract-secret-" + "x" * 32
BASE_URL = "http://bot-contract.test"
TG_ID = 222_000_222
RealSession = requests.Session


class WSGIAdapter(requests.adapters.BaseAdapter):
    """Sends a requests.Session's requests to a Flask app."""

    def __init__(self, app, session):
        super().__init__()
        self.client = app.test_client(use_cookies=False)
        self.session = session

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        parts = urlsplit(request.url)
        body = request.body or b""
        if isinstance(body, str):
            body = body.encode()
        # urllib3 would undo Content-Encoding; this adapter asks for none.
        headers = {k: v for k, v in request.headers.items() if k.lower() != "accept-encoding"}
        reply = self.client.open(
            parts.path,
            method=request.method,
            query_string=parts.query,
            data=body,
            headers=headers,
        )
        for header in reply.headers.getlist("Set-Cookie"):
            for name, morsel in SimpleCookie(header).items():
                if morsel["expires"] and "1970" in morsel["expires"] or not morsel.value:
                    self.session.cookies.pop(name, None)
                else:
                    self.session.cookies.set(name, morsel.value)

        response = requests.Response()
        response.status_code = reply.status_code
        response.headers = CaseInsensitiveDict(reply.headers)
        response._content = reply.get_data()
        response.encoding = "utf-8"
        response.url = request.url
        response.request = request
        return response

    def close(self):
        pass


@pytest.fixture
def wired(app, monkeypatch):
    """requests.Session in the bot's auth client now reaches the app."""
    from flask import g

    app.config["TELEGRAM_BOT_API_SECRET"] = SECRET

    # One app context for the whole test: forget the user Flask-Login cached
    # in g, as every real request starts without one.
    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)

    def session_factory():
        session = RealSession()
        session.mount("http://", WSGIAdapter(app, session))
        return session

    monkeypatch.setattr(bot_auth.requests, "Session", session_factory)
    return session_factory


@pytest.fixture
def bot_api(wired, user):
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=TG_ID))
    db.session.commit()
    return TelegramAuthClient(BASE_URL, SECRET).login(TelegramUser(id=TG_ID, username="alice_tg"))


def test_a_signed_in_bot_reads_its_day(bot_api):
    day = bot_api.get_day()

    assert isinstance(day["meals"], list)
    assert bot_api.expired is False


def test_endpoints_closed_to_the_bot_say_so_without_ending_the_session(bot_api):
    with pytest.raises(NosiFitAPIError) as raised:
        bot_api._request("GET", "/api/dashboard/today")

    assert raised.value.code == "telegram_session_scope"
    assert str(raised.value) == ERROR_MESSAGES["telegram_session_scope"]
    assert bot_api.expired is False


def test_a_missing_meal_gets_its_own_message(bot_api):
    with pytest.raises(NosiFitAPIError) as raised:
        bot_api.delete_meal(999_999)

    assert raised.value.code == "meal_not_found"
    assert str(raised.value) == ERROR_MESSAGES["meal_not_found"]


def test_a_revoked_session_asks_to_log_in_again(bot_api, user):
    TelegramIdentity.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    with pytest.raises(NosiFitAPIError) as raised:
        bot_api.get_day()

    assert raised.value.code == "session_expired"
    assert bot_api.expired is True


def test_no_session_at_all_gets_401_and_asks_to_log_in(wired):
    session = wired()
    session.cookies.set("session", "not-a-real-session")
    api = NosiFitAPI(base_url=BASE_URL, session=session)

    with pytest.raises(NosiFitAPIError) as raised:
        api.get_day()

    assert raised.value.code == "session_expired"
    assert api.expired is True


def test_an_unlinked_telegram_account_is_told_so(wired):
    with pytest.raises(bot_auth.TelegramAuthError) as raised:
        TelegramAuthClient(BASE_URL, SECRET).login(TelegramUser(id=999_999))

    assert raised.value.code == "not_linked"
