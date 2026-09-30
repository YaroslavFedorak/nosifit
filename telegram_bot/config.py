import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    nosi_fit_base_url: str
    nosi_fit_email: str
    nosi_fit_password: str
    redis_url: str | None

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        email = os.getenv("NOSI_FIT_EMAIL")
        if not email:
            raise RuntimeError("NOSI_FIT_EMAIL is not set")

        password = os.getenv("NOSI_FIT_PASSWORD")
        if not password:
            raise RuntimeError("NOSI_FIT_PASSWORD is not set")

        return cls(
            bot_token=token,
            nosi_fit_base_url=os.getenv(
                "NOSI_FIT_BASE_URL", "http://localhost:5000"
            ).rstrip("/"),
            nosi_fit_email=email.strip().lower(),
            nosi_fit_password=password,
            redis_url=os.getenv("NOSI_FIT_REDIS_URL") or None,
        )
