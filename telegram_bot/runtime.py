from functools import lru_cache

from telegram_bot.config import TelegramConfig
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError


@lru_cache(maxsize=1)
def get_config() -> TelegramConfig:
    return TelegramConfig.from_env()


_sessions: dict[int, NosiFitAPI] = {}


def authenticate(user_id: int, email: str, password: str) -> NosiFitAPI:
    api = NosiFitAPI(base_url=get_config().nosi_fit_base_url)
    api.login(email.strip().lower(), password)
    _sessions[user_id] = api
    return api


def get_api(user_id: int) -> NosiFitAPI:
    try:
        return _sessions[user_id]
    except KeyError as exc:
        raise NosiFitAPIError(
            "Ви не авторизовані в NosiFit. Натисніть «🔐 Увійти»."
        ) from exc


def is_authenticated(user_id: int) -> bool:
    return user_id in _sessions


def logout(user_id: int) -> None:
    _sessions.pop(user_id, None)
