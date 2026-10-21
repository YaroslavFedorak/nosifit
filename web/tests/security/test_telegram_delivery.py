"""How updates reach the Telegram bot: webhook mode and the session
middleware that keeps network calls out of the event loop."""

import asyncio
import threading
from types import SimpleNamespace

import pytest
from aiogram import Bot, Dispatcher
from aiohttp.test_utils import TestClient, TestServer

from telegram_bot.bot import WEBHOOK_PATH, create_webhook_app
from telegram_bot import runtime
from telegram_bot.config import TelegramConfig


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:" + "A" * 35)
    monkeypatch.setenv("TELEGRAM_BOT_API_SECRET", "s" * 40)
    for name in ("TELEGRAM_WEBHOOK_URL", "TELEGRAM_WEBHOOK", "RAILWAY_PUBLIC_DOMAIN"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_polling_without_webhook_url(env):
    assert TelegramConfig.from_env().webhook_url == ""


def test_webhook_url_from_railway_domain(env):
    env.setenv("TELEGRAM_WEBHOOK", "1")
    env.setenv("RAILWAY_PUBLIC_DOMAIN", "bot.up.railway.app")
    assert TelegramConfig.from_env().webhook_url == "https://bot.up.railway.app"


def test_plain_http_webhook_is_refused(env):
    env.setenv("TELEGRAM_WEBHOOK_URL", "http://bot.example")
    with pytest.raises(RuntimeError):
        TelegramConfig.from_env()


def test_webhook_secret_is_not_the_api_secret(env):
    config = TelegramConfig.from_env()
    assert len(config.webhook_secret) == 64
    assert config.webhook_secret != config.api_secret


def test_webhook_rejects_requests_without_the_secret(env):
    env.setenv("TELEGRAM_WEBHOOK_URL", "https://bot.example")
    config = TelegramConfig.from_env()

    async def run():
        app = create_webhook_app(Bot(config.bot_token), Dispatcher(), config)
        async with TestClient(TestServer(app)) as client:
            assert (await client.get("/health")).status == 200
            assert (await client.post(WEBHOOK_PATH, json={})).status == 401
            wrong = {"X-Telegram-Bot-Api-Secret-Token": "nope"}
            assert (await client.post(WEBHOOK_PATH, json={}, headers=wrong)).status == 401

    asyncio.run(run())


def _event(chat_type="private", is_bot=False):
    user = SimpleNamespace(id=7, is_bot=is_bot)
    return SimpleNamespace(chat=SimpleNamespace(type=chat_type), from_user=user), user


def _run_middleware(monkeypatch, chat_type="private", is_bot=False):
    threads = []
    monkeypatch.setattr(runtime, "restore", lambda uid: threads.append(threading.get_ident()))
    event, user = _event(chat_type, is_bot)

    async def handler(_event, _data):
        return "handled"

    async def run():
        return await runtime.SessionMiddleware()(handler, event, {"event_from_user": user})

    assert asyncio.run(run()) == "handled"
    return threads


def test_session_is_restored_off_the_event_loop(monkeypatch):
    threads = _run_middleware(monkeypatch)
    assert len(threads) == 1 and threads[0] != threading.get_ident()


@pytest.mark.parametrize("chat_type,is_bot", [("group", False), ("supergroup", False), ("private", True)])
def test_groups_and_bots_cause_no_restore(monkeypatch, chat_type, is_bot):
    assert _run_middleware(monkeypatch, chat_type, is_bot) == []
