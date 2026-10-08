from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram_bot.config import TelegramConfig
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError
from telegram_bot.services.telegram_auth import TelegramAuthClient, TelegramUser


@lru_cache(maxsize=1)
def get_config() -> TelegramConfig:
    return TelegramConfig.from_env()


@lru_cache(maxsize=1)
def auth_client() -> TelegramAuthClient:
    config = get_config()
    return TelegramAuthClient(config.nosi_fit_base_url, config.api_secret)


# NosiFit sessions per Telegram user id (the canonical identity, never the
# username). Kept in memory: after a restart users press "Log in" once.
_sessions: dict[int, NosiFitAPI] = {}


def login(user: TelegramUser) -> NosiFitAPI:
    api = auth_client().login(user)
    _sessions[user.id] = api
    return api


def register_start(user: TelegramUser, email: str) -> None:
    auth_client().register_start(user, email)


def register_verify(user: TelegramUser, email: str, code: str) -> NosiFitAPI:
    api = auth_client().register_verify(user, email, code)
    _sessions[user.id] = api
    return api


def link_url(user: TelegramUser, via: str = "password") -> tuple[str, int]:
    return auth_client().link_url(user, via)


def get_api(user_id: int) -> NosiFitAPI:
    api = _sessions.get(user_id)
    if api is None or api.expired:
        _sessions.pop(user_id, None)
        raise NosiFitAPIError(
            "Спочатку увійдіть: /start → «Увійти»."
        )
    return api


def is_authenticated(user_id: int) -> bool:
    api = _sessions.get(user_id)
    if api is not None and api.expired:
        _sessions.pop(user_id, None)
        return False
    return api is not None


def logout(user_id: int) -> None:
    _sessions.pop(user_id, None)


def local_now() -> datetime:
    """Current time in the users' timezone (the server may run in UTC)."""
    try:
        return datetime.now(ZoneInfo(get_config().timezone))
    except (ZoneInfoNotFoundError, RuntimeError):
        return datetime.now()
