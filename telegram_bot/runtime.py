from functools import lru_cache

from telegram_bot.config import TelegramConfig
from telegram_bot.services.api import NosiFitAPI


@lru_cache(maxsize=1)
def get_config() -> TelegramConfig:
    return TelegramConfig.from_env()


@lru_cache(maxsize=1)
def get_api() -> NosiFitAPI:
    config = get_config()
    return NosiFitAPI(
        base_url=config.nosi_fit_base_url,
        email=config.nosi_fit_email,
        password=config.nosi_fit_password,
    )
