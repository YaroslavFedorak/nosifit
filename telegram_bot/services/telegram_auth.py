"""Signed calls from the bot to the web app's /api/telegram/* endpoints.

The bot never sees a NosiFit password. It tells the web app which Telegram
user (numeric id from the update) is acting, and proves that it is the bot
by signing the request with TELEGRAM_BOT_API_SECRET.
"""

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

from backend.app.utils.bot_signature import sign_request
from telegram_bot.services.api import NosiFitAPI, NosiFitAPIError


class TelegramAuthError(NosiFitAPIError):
    """``code`` is the web app's error code (not_linked, invalid_code, ...)."""


@dataclass(frozen=True)
class TelegramUser:
    """What the bot forwards about the Telegram user. ``id`` is the identity."""

    id: int
    username: str | None = None
    name: str | None = None

    @classmethod
    def from_aiogram(cls, user) -> "TelegramUser":
        name = " ".join(
            part for part in (user.first_name, user.last_name) if part
        ).strip()
        return cls(id=int(user.id), username=user.username or None, name=name or None)

    def payload(self) -> dict:
        return {
            "telegram_user_id": self.id,
            "username": self.username,
            "name": self.name,
        }


class TelegramAuthClient:
    def __init__(self, base_url: str, secret: str, timeout: float = 15):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout

    def _post(self, session: requests.Session, path: str, payload: dict) -> requests.Response:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload, separators=(",", ":")).encode()
        headers = {
            "Content-Type": "application/json",
            **sign_request(self.secret, "POST", urlsplit(url).path, body),
        }
        try:
            response = session.post(
                url, data=body, headers=headers, timeout=self.timeout, allow_redirects=False
            )
        except requests.RequestException as exc:
            raise TelegramAuthError("Не вдалося підключитися до NosiFit.", "unavailable") from exc

        if response.ok:
            return response

        try:
            code = response.json().get("code")
        except (ValueError, AttributeError):
            code = None
        if response.status_code == 429:
            code = code if code == "too_many_attempts" else "rate_limited"
        raise TelegramAuthError(code or "error", code or "error")

    def login(self, user: TelegramUser) -> NosiFitAPI:
        """A NosiFit session for this Telegram user (TelegramAuthError not_linked)."""
        session = requests.Session()
        self._post(session, "/api/telegram/login", user.payload())
        return NosiFitAPI(base_url=self.base_url, session=session)

    def register_start(self, user: TelegramUser, email: str) -> None:
        self._post(
            requests.Session(), "/api/telegram/register/start", {**user.payload(), "email": email}
        )

    def register_verify(self, user: TelegramUser, email: str, code: str) -> NosiFitAPI:
        session = requests.Session()
        self._post(
            session,
            "/api/telegram/register/verify",
            {**user.payload(), "email": email, "code": code},
        )
        return NosiFitAPI(base_url=self.base_url, session=session)

    def link_url(self, user: TelegramUser) -> tuple[str, int]:
        data = self._post(requests.Session(), "/api/telegram/link-token", user.payload()).json()
        return str(data["url"]), int(data.get("expires_in") or 600)
