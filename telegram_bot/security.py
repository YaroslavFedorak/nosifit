"""Guards for the bot's login flow.

- The bot works only in private chats. In a group the email and password
  would be visible to every member (a bot without admin rights cannot delete
  them) and the user's NosiFit data would be posted to the group.
- Login attempts are limited per Telegram user. Every login goes to the web
  app from the bot's single IP, so one abusive Telegram account could
  otherwise use up the server's per-IP limit and lock out all bot users.
"""

import threading
import time


def is_private_chat(event) -> bool:
    chat = getattr(event, "chat", None)
    if chat is None:  # CallbackQuery: the chat is on its message
        message = getattr(event, "message", None)
        chat = getattr(message, "chat", None)
    return getattr(chat, "type", None) == "private"


class LoginThrottle:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 15 * 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._attempts: dict[int, list[float]] = {}

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        with self._lock:
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


login_throttle = LoginThrottle()
