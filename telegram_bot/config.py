import os
from dataclasses import dataclass

from dotenv import load_dotenv

from backend.app.utils.bot_signature import MIN_SECRET_LENGTH

load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    nosi_fit_base_url: str
    # Shared with the web service; signs the bot's /api/telegram/* requests.
    api_secret: str
    timezone: str = "Europe/Kyiv"

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        secret = os.getenv("TELEGRAM_BOT_API_SECRET") or ""
        if len(secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                "TELEGRAM_BOT_API_SECRET must be set to the same random value "
                f"(at least {MIN_SECRET_LENGTH} characters) on the bot and web services"
            )

        return cls(
            bot_token=token,
            nosi_fit_base_url=os.getenv(
                "NOSI_FIT_BASE_URL", "http://localhost:5000"
            ).rstrip("/"),
            api_secret=secret,
            timezone=os.getenv("NOSI_FIT_TIMEZONE", "Europe/Kyiv"),
        )
