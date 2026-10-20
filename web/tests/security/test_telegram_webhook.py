"""Webhook mode of the Telegram bot: config and the aiohttp endpoint."""

import asyncio

import pytest
from aiogram import Bot, Dispatcher
from aiohttp.test_utils import TestClient, TestServer

from telegram_bot.bot import WEBHOOK_PATH, create_webhook_app
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
