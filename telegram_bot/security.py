"""Guards for the bot.

- The bot works only in private chats. In a group, codes and links would be
  visible to every member (a bot without admin rights cannot delete them),
  the user's NosiFit data would be posted to the group, and "who pressed the
  button" would be ambiguous. Group updates are dropped and the bot leaves
  groups it is added to.
- Updates without a human sender (channels, other bots) are dropped: the
  sender's numeric Telegram id is the identity everything is keyed on.
- Actions are throttled per Telegram user in the bot as well. The web app
  enforces the authoritative limits (Redis, per Telegram id and email); this
  only keeps one noisy user from flooding the bot's single outbound IP.
"""

import threading
import time


def _chat_of(event):
    chat = getattr(event, "chat", None)
    if chat is None:  # CallbackQuery: the chat is on its message
        message = getattr(event, "message", None)
        chat = getattr(message, "chat", None)
    return chat


def is_private_chat(event) -> bool:
    return getattr(_chat_of(event), "type", None) == "private"


def is_human_sender(event) -> bool:
    user = getattr(event, "from_user", None)
    return (
        user is not None
        and not getattr(user, "is_bot", True)
        and isinstance(getattr(user, "id", None), int)
        and user.id > 0
    )


def is_private_human(event) -> bool:
    return is_private_chat(event) and is_human_sender(event)


class LoginThrottle:
    """Fixed number of attempts per Telegram user and time window."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 15 * 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._attempts: dict[int, list[float]] = {}

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._attempts) > 50_000:
                self._attempts = {
                    k: v for k, v in self._attempts.items()
                    if v and now - v[-1] < self.window_seconds
                }
            recent = [
                t for t in self._attempts.get(user_id, []) if now - t < self.window_seconds
            ]
            if len(recent) >= self.max_attempts:
                self._attempts[user_id] = recent
                return False
            recent.append(now)
            self._attempts[user_id] = recent
            return True

    def reset(self, user_id: int) -> None:
        with self._lock:
            self._attempts.pop(user_id, None)


login_throttle = LoginThrottle(max_attempts=10, window_seconds=15 * 60)
start_throttle = LoginThrottle(max_attempts=20, window_seconds=60)
register_throttle = LoginThrottle(max_attempts=5, window_seconds=60 * 60)
code_throttle = LoginThrottle(max_attempts=10, window_seconds=10 * 60)
link_throttle = LoginThrottle(max_attempts=5, window_seconds=15 * 60)
# Barcode photos are decoded on the bot's machine: cap the CPU one user can use.
barcode_throttle = LoginThrottle(max_attempts=10, window_seconds=60)
