import logging
import math
import time
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram_bot.config import TelegramConfig
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError
from telegram_bot.services.telegram_auth import TelegramAuthClient, TelegramAuthError, TelegramUser

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_config() -> TelegramConfig:
    return TelegramConfig.from_env()


@lru_cache(maxsize=1)
def auth_client() -> TelegramAuthClient:
    config = get_config()
    return TelegramAuthClient(config.nosi_fit_base_url, config.api_secret)


# NosiFit sessions per Telegram user id (the canonical identity, never the
# username). Only a cache: the Telegram <-> NosiFit link lives in PostgreSQL
# (telegram_identities), so after a restart or redeploy the session is
# restored on first use instead of asking the user to log in again.
_sessions: dict[int, NosiFitAPI] = {}

# Telegram ids the web app had no session for (not linked, logged out in the
# bot, web app unreachable) and when it said so; asked again after
# RESTORE_RETRY_SECONDS. /logout stores math.inf: never, until a login.
_no_restore: dict[int, float] = {}
RESTORE_RETRY_SECONDS = 60


def _remember(user_id: int, api: NosiFitAPI) -> NosiFitAPI:
    _sessions[user_id] = api
    _no_restore.pop(user_id, None)
    return api


def login(user: TelegramUser) -> NosiFitAPI:
    return _remember(user.id, auth_client().login(user))


def register_start(user: TelegramUser, email: str) -> None:
    auth_client().register_start(user, email)


def register_verify(user: TelegramUser, email: str, code: str) -> NosiFitAPI:
    return _remember(user.id, auth_client().register_verify(user, email, code))


def link_url(user: TelegramUser, via: str = "password") -> tuple[str, int]:
    return auth_client().link_url(user, via)


def restore(user_id: int) -> NosiFitAPI | None:
    """The user's session: cached, or reopened from the stored link."""
    api = _sessions.get(user_id)
    if api is not None and not api.expired:
        return api
    _sessions.pop(user_id, None)

    asked_at = _no_restore.get(user_id)
    if asked_at is not None and time.monotonic() - asked_at < RESTORE_RETRY_SECONDS:
        return None
    try:
        api = auth_client().restore(user_id)
    except TelegramAuthError as exc:
        if exc.code not in ("not_linked", "logged_out"):
            logger.warning("Telegram session restore failed: %s", exc.code)
        _no_restore[user_id] = time.monotonic()
        return None
    except Exception:
        logger.exception("Telegram session restore failed")
        _no_restore[user_id] = time.monotonic()
        return None
    return _remember(user_id, api)


def get_api(user_id: int) -> NosiFitAPI:
    api = restore(user_id)
    if api is None:
        raise NosiFitAPIError(
            "Спочатку увійдіть: /start → «Увійти»."
        )
    return api


def is_authenticated(user_id: int) -> bool:
    return restore(user_id) is not None


def logout(user_id: int) -> None:
    _sessions.pop(user_id, None)
    _no_restore[user_id] = math.inf
    # Stored by the web app, so the logout survives the bot's restarts.
    try:
        auth_client().logout(user_id)
    except Exception:
        logger.exception("Telegram logout could not be stored")


def local_now() -> datetime:
    """Current time in the users' timezone (the server may run in UTC)."""
    try:
        return datetime.now(ZoneInfo(get_config().timezone))
    except (ZoneInfoNotFoundError, RuntimeError):
        return datetime.now()
