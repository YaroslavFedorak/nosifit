import hashlib
import hmac
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from shared.bot_signature import MIN_SECRET_LENGTH

load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    nosi_fit_base_url: str
    # Shared with the web service; signs the bot's /api/telegram/* requests.
    api_secret: str
    timezone: str = "Europe/Kyiv"
    # Public https base of the bot service. Set → webhook mode; unset → polling.
    webhook_url: str = ""
    # Telegram repeats it in every webhook request; derived from api_secret.
    webhook_secret: str = ""
    port: int = 8080

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
            webhook_url=_webhook_url(),
            webhook_secret=hmac.new(
                secret.encode(), b"telegram-webhook", hashlib.sha256
            ).hexdigest(),
            port=int(os.getenv("PORT", "8080")),
        )


def _webhook_url() -> str:
    """TELEGRAM_WEBHOOK_URL, or the Railway domain once TELEGRAM_WEBHOOK=1."""
    url = os.getenv("TELEGRAM_WEBHOOK_URL", "").strip()
    if not url and os.getenv("TELEGRAM_WEBHOOK") == "1":
        domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
        url = f"https://{domain}" if domain else ""
    if url and not url.startswith("https://"):
        raise RuntimeError("TELEGRAM_WEBHOOK_URL must start with https://")
    return url.rstrip("/")
