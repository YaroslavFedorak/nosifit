"""Telegram bot handlers, driven through the real aiogram dispatcher.

Telegram itself is replaced by a recording session (every Bot API call is
captured); the web app is replaced by stubs of telegram_bot.runtime, except
in the signature round trip, which goes through the Flask app.
"""

import asyncio
import json
import logging
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    GetMe,
    LeaveChat,
    SendMessage,
)
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Message,
    Update,
)
from aiogram.types import User as TgUser

from telegram_bot import runtime
from telegram_bot.bot import create_dispatcher
from telegram_bot.services.api import NosiFitAPI
from telegram_bot.services.telegram_auth import TelegramAuthError, TelegramUser

ALICE = TgUser(id=111, is_bot=False, first_name="Alice", username="alice_tg")


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(
                message_id=1000 + len(self.calls),
                date=datetime.now(),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=method.text,
            )
        if isinstance(method, GetMe):
            return TgUser(id=1, is_bot=True, first_name="NosiFit", username="NosiFitBot")
        return True

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def close(self):
        pass


def fresh_dispatcher():
    """Routers are module singletons; detach them from an earlier dispatcher."""
    from telegram_bot.handlers import auth, common, nutrition, start, water, weight

    for module in (auth, common, nutrition, start, water, weight):
        module.router._parent_router = None
    return create_dispatcher()


class Harness:
    def __init__(self):
        self.session = RecordingSession()
        self.bot = Bot(token="123456:TEST-TOKEN-not-real-0000000000000", session=self.session)
        self.dispatcher = fresh_dispatcher()
        self.loop = asyncio.new_event_loop()
        self._ids = 0

    def _next(self):
        self._ids += 1
        return self._ids

    def feed(self, update):
        return self.loop.run_until_complete(self.dispatcher.feed_update(self.bot, update))

    def message(self, text, user=ALICE, chat_type="private", chat_id=None):
        return self.feed(
            Update(
                update_id=self._next(),
                message=Message(
                    message_id=self._next(),
                    date=datetime.now(),
                    chat=Chat(id=chat_id or user.id, type=chat_type),
                    from_user=user,
                    text=text,
                ),
            )
        )

    def callback(self, data, user=ALICE, chat_type="private"):
        return self.feed(
            Update(
                update_id=self._next(),
                callback_query=CallbackQuery(
                    id=str(self._next()),
                    from_user=user,
                    chat_instance="ci",
                    data=data,
                    message=Message(
                        message_id=self._next(),
                        date=datetime.now(),
                        chat=Chat(id=user.id, type=chat_type),
                        text="menu",
                    ),
                ),
            )
        )

    def sent(self):
        return [c for c in self.session.calls if isinstance(c, SendMessage)]

    def texts(self):
        return [c.text for c in self.sent()]

    def close(self):
        self.loop.run_until_complete(self.bot.session.close())
        self.loop.close()


@pytest.fixture
def bot(monkeypatch):
    from telegram_bot import security

    for throttle in (
        security.login_throttle,
        security.start_throttle,
        security.register_throttle,
        security.code_throttle,
        security.link_throttle,
    ):
        throttle._attempts.clear()
    runtime._sessions.clear()
    harness = Harness()
    yield harness
    harness.close()
    runtime._sessions.clear()


@pytest.fixture
def backend(monkeypatch):
    """Stub of the web app as seen through telegram_bot.runtime."""
    calls = {"login": [], "register_start": [], "register_verify": [], "link_url": []}
    behaviour = {}

    def make(name, result):
        def fake(*args):
            calls[name].append(args)
            error = behaviour.get(name)
            if error:
                raise TelegramAuthError(error, error)
            value = result(*args)
            return value

        return fake

    def fake_login(user):
        api = NosiFitAPI(base_url="http://test")
        api.session.cookies.set("session", "x")
        runtime._sessions[user.id] = api
        return api

    def fake_verify(user, email, code):
        return fake_login(user)

    monkeypatch.setattr(runtime, "login", make("login", fake_login))
    monkeypatch.setattr(runtime, "register_start", make("register_start", lambda *a: None))
    monkeypatch.setattr(runtime, "register_verify", make("register_verify", fake_verify))
    monkeypatch.setattr(
        runtime,
        "link_url",
        make(
            "link_url",
            lambda user, via="password": (
                f"https://nosifit.example/auth/telegram/link/{'T' * 43}?via={via}",
                600,
            ),
        ),
    )
    return calls, behaviour


# --- Private chats with humans only ----------------------------------------------------------


@pytest.mark.parametrize("chat_type", ["group", "supergroup", "channel"])
def test_auth_flows_are_ignored_outside_private_chats(bot, backend, chat_type):
    calls, _ = backend
    assert bot.message("/start", chat_type=chat_type, chat_id=-100) is UNHANDLED
    assert bot.message("/register", chat_type=chat_type, chat_id=-100) is UNHANDLED
    assert bot.callback("auth:login", chat_type=chat_type) is UNHANDLED
    assert bot.callback("auth:connect", chat_type=chat_type) is UNHANDLED
    assert bot.session.calls == [] and all(not v for v in calls.values())


def test_other_bots_are_ignored(bot, backend):
    robot = TgUser(id=222, is_bot=True, first_name="Robot")
    assert bot.message("/start", user=robot) is UNHANDLED
    assert bot.callback("auth:login", user=robot) is UNHANDLED


def test_bot_leaves_groups_it_is_added_to(bot):
    update = Update(
        update_id=1,
        my_chat_member=ChatMemberUpdated(
            chat=Chat(id=-100, type="group"),
            from_user=ALICE,
            date=datetime.now(),
            old_chat_member=ChatMemberLeft(user=TgUser(id=1, is_bot=True, first_name="b")),
            new_chat_member=ChatMemberMember(user=TgUser(id=1, is_bot=True, first_name="b")),
        ),
    )
    bot.feed(update)
    assert any(isinstance(c, LeaveChat) and c.chat_id == -100 for c in bot.session.calls)


# --- /start and the menu --------------------------------------------------------------------


def test_start_offers_login_register_help(bot, backend):
    bot.message("/start")

    markup = bot.sent()[-1].reply_markup
    data = [row[0].callback_data for row in markup.inline_keyboard]
    assert data == ["auth:login", "auth:register", "auth:help"]
    assert "Ласкаво просимо до NosiFit" in bot.texts()[0]


def test_start_is_throttled(bot, backend):
    for _ in range(25):
        bot.message("/start")
    assert len(bot.sent()) == 40  # 20 allowed, two messages each


def test_nothing_ever_asks_for_a_password(bot, backend):
    for step in ("/start", "/login", "/register", "user@example.com", "123456", "/connect", "/help"):
        bot.message(step)
    bot.callback("auth:help")

    for text in bot.texts():
        assert "Введіть пароль" not in text and "password" not in text.lower()


# --- Log in -----------------------------------------------------------------------------------


def test_login_uses_the_numeric_telegram_id(bot, backend):
    calls, _ = backend
    bot.callback("auth:login")

    (user,), = calls["login"]
    assert user == TelegramUser(id=111, username="alice_tg", name="Alice")
    assert "✅ Ви увійшли в NosiFit." in bot.texts()
    assert any(isinstance(c, AnswerCallbackQuery) for c in bot.session.calls)
    assert runtime.is_authenticated(111)


def test_username_substitution_reaches_the_server_as_a_different_id(bot, backend):
    calls, _ = backend
    impostor = TgUser(id=999, is_bot=False, first_name="Alice", username="alice_tg")

    bot.callback("auth:login", user=impostor)

    assert calls["login"][0][0].id == 999


def test_unknown_telegram_is_asked_how_it_signs_in(bot, backend):
    """One "Log in" button; first time it asks for the website sign-in method."""
    _, behaviour = backend
    behaviour["login"] = "not_linked"

    bot.callback("auth:login")

    last = bot.sent()[-1]
    assert "ще не підключено" in last.text and "Як ви входите" in last.text
    assert [r[0].callback_data for r in last.reply_markup.inline_keyboard] == [
        "auth:connect:google",
        "auth:connect:github",
        "auth:connect:password",
        "auth:register",
    ]
    assert not runtime.is_authenticated(111)


def test_server_errors_are_generic(bot, backend):
    _, behaviour = backend
    behaviour["login"] = "Traceback: psycopg.OperationalError at db.internal:5432"

    bot.callback("auth:login")

    assert "psycopg" not in bot.texts()[-1] and "Щось пішло не так" in bot.texts()[-1]


def test_logout_forgets_the_session(bot, backend):
    bot.callback("auth:login")
    bot.message("/logout")
    assert not runtime.is_authenticated(111)


def test_expired_session_is_dropped():
    api = NosiFitAPI(base_url="http://test")
    runtime._sessions[5] = api
    api.expired = True
    assert not runtime.is_authenticated(5)
    assert 5 not in runtime._sessions


# --- Create an account ------------------------------------------------------------------------


def test_registration_flow(bot, backend):
    calls, _ = backend
    bot.callback("auth:register")
    bot.message("New.User@Example.com")
    bot.message("123456")

    assert calls["register_start"][0][1] == "new.user@example.com"
    user, email, code = calls["register_verify"][0]
    assert (user.id, email, code) == (111, "new.user@example.com", "123456")
    # The code message is deleted from the chat.
    assert any(isinstance(c, DeleteMessage) for c in bot.session.calls)
    assert any("акаунт NosiFit створено" in t for t in bot.texts())
    assert runtime.is_authenticated(111)


def test_registration_answer_does_not_reveal_existing_accounts(bot, backend):
    """The bot shows one text; the server answers the same for both cases."""
    bot.callback("auth:register")
    bot.message("someone@example.com")
    text = bot.texts()[-1]
    assert "Якщо з цією адресою вже є акаунт" in text


def test_invalid_email_is_asked_again(bot, backend):
    calls, _ = backend
    bot.callback("auth:register")
    bot.message("not-an-email")
    bot.message("x" * 200 + "@example.com")
    assert calls["register_start"] == []


def test_wrong_codes_are_limited_in_the_bot_too(bot, backend):
    calls, behaviour = backend
    behaviour["register_verify"] = "invalid_code"
    bot.callback("auth:register")
    bot.message("a@example.com")

    for _ in range(7):
        bot.message("000000")

    assert len(calls["register_verify"]) == 5
    assert any("Забагато спроб" in text for text in bot.texts())


def test_non_numeric_codes_are_not_sent(bot, backend):
    calls, _ = backend
    bot.callback("auth:register")
    bot.message("a@example.com")
    bot.message("12ab56")
    bot.message("1234567")
    assert calls["register_verify"] == []


def test_commands_escape_the_registration_state(bot, backend):
    calls, _ = backend
    bot.callback("auth:register")
    bot.message("/cancel")
    bot.message("a@example.com")
    assert calls["register_start"] == []


def test_resend_code(bot, backend):
    calls, _ = backend
    bot.callback("auth:register")
    bot.message("a@example.com")
    bot.callback("auth:resend")
    assert [c[1] for c in calls["register_start"]] == ["a@example.com", "a@example.com"]


def test_existing_email_conflict_points_to_connect(bot, backend):
    _, behaviour = backend
    behaviour["register_verify"] = "email_unavailable"
    bot.callback("auth:register")
    bot.message("a@example.com")
    bot.message("123456")
    assert "Підключити акаунт" in bot.texts()[-1]


def test_codes_and_emails_are_not_logged(bot, backend, caplog):
    _, behaviour = backend
    caplog.set_level(logging.DEBUG)
    behaviour["register_verify"] = "weird_error"
    bot.callback("auth:register")
    bot.message("secret.person@example.com")
    bot.message("424242")

    assert "424242" not in caplog.text
    assert "secret.person@example.com" not in caplog.text


# --- Connect an existing account ---------------------------------------------------------


@pytest.mark.parametrize(
    "via, label",
    [
        ("google", "Увійти через Google"),
        ("github", "Увійти через GitHub"),
        ("password", "Увійти з email і паролем"),
    ],
)
def test_each_sign_in_method_gets_its_own_protected_link(bot, backend, via, label):
    calls, _ = backend
    bot.callback(f"auth:connect:{via}")

    message = bot.sent()[-1]
    user, requested_via = calls["link_url"][0]
    assert (user.id, requested_via) == (111, via)
    assert message.protect_content is True
    button = message.reply_markup.inline_keyboard[0][0]
    assert label in button.text
    assert button.url.startswith("https://nosifit.example/auth/telegram/link/")
    assert "пароль" not in message.text.lower() or via == "password"


def test_unknown_method_is_not_sent_to_the_server(bot, backend):
    calls, _ = backend
    bot.callback("auth:connect:evil")
    assert calls["link_url"] == []


def test_connect_command_and_old_buttons_show_the_method_choice(bot, backend):
    calls, _ = backend
    bot.callback("auth:connect")  # button from an older message
    bot.message("/connect")
    bot.message("/start connect")  # profile page's "Connect Telegram"

    assert calls["link_url"] == []
    menus = [m.reply_markup for m in bot.sent()[-3:]]
    assert all(m.inline_keyboard[0][0].callback_data == "auth:connect:google" for m in menus)


def test_already_linked_telegram_is_told_to_log_in(bot, backend):
    _, behaviour = backend
    behaviour["link_url"] = "already_linked"
    bot.callback("auth:connect:google")
    assert "уже підключено" in bot.texts()[-1]


# --- The bot's signature is accepted by the web app -------------------------------------


def test_signed_client_round_trip(app, client, monkeypatch):
    from backend.app.extensions import db
    from backend.app.models.telegram import TelegramIdentity
    from backend.app.models.user import User
    from telegram_bot.services.telegram_auth import TelegramAuthClient

    secret = "round-trip-secret-" + "z" * 40
    app.config["TELEGRAM_BOT_API_SECRET"] = secret
    user = User(username="u", email="rt@example.com", password="oauth")
    db.session.add(user)
    db.session.commit()
    db.session.add(TelegramIdentity(user_id=user.id, telegram_user_id=4242))
    db.session.commit()

    class Forwarded:
        def __init__(self, response):
            self.status_code = response.status_code
            self.ok = response.status_code < 400
            self._json = response.json

        def json(self):
            return self._json

    def forward(self, url, data=None, headers=None, **kwargs):
        path = url.split("http://bot.test", 1)[1]
        return Forwarded(client.post(path, data=data, headers=headers))

    monkeypatch.setattr("requests.Session.post", forward)
    auth = TelegramAuthClient("http://bot.test", secret)

    api = auth.login(TelegramUser(id=4242, username="rt"))
    assert isinstance(api, NosiFitAPI)

    with pytest.raises(TelegramAuthError) as missing:
        auth.login(TelegramUser(id=4343))
    assert missing.value.code == "not_linked"

    wrong = TelegramAuthClient("http://bot.test", "another-secret-" + "q" * 40)
    with pytest.raises(TelegramAuthError):
        wrong.login(TelegramUser(id=4242))


def test_bot_refuses_to_start_without_a_strong_secret(monkeypatch):
    from telegram_bot.config import TelegramConfig

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:x")
    monkeypatch.setenv("TELEGRAM_BOT_API_SECRET", "short")
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_API_SECRET"):
        TelegramConfig.from_env()

    monkeypatch.setenv("TELEGRAM_BOT_API_SECRET", "s" * 64)
    assert TelegramConfig.from_env().api_secret == "s" * 64


def test_signed_body_is_exactly_what_is_sent(monkeypatch):
    """The client signs the bytes it posts (compact JSON), path from the URL."""
    from backend.app.utils.bot_signature import check_signature
    from telegram_bot.services.telegram_auth import TelegramAuthClient

    captured = {}

    class Ok:
        ok, status_code = True, 200

        def json(self):
            return {"url": "u", "expires_in": 600}

    def capture(self, url, data=None, headers=None, **kwargs):
        captured.update(url=url, data=data, headers=headers)
        return Ok()

    monkeypatch.setattr("requests.Session.post", capture)
    TelegramAuthClient("https://web.example/", "k" * 40).link_url(TelegramUser(id=1))

    assert json.loads(captured["data"])["telegram_user_id"] == 1
    assert check_signature(
        "k" * 40, captured["headers"], "POST", "/api/telegram/link-token", captured["data"]
    )
