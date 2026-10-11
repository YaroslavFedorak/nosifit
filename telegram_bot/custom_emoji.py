"""NosiFit custom emoji in outgoing bot messages.

Handlers keep writing standard emoji (🔥, 🥩, ...). For every icon in
``telegram_bot/emoji/icons.json`` that has a real ``custom_emoji_id``, this
request middleware wraps its fallback emoji in HTML text as
``<tg-emoji emoji-id="...">🔥</tg-emoji>``. Icons without an ID are left as
plain emoji, so with no registered pack nothing changes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import Default
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod
from aiogram.methods.base import Response, TelegramType

ICONS_PATH = Path(__file__).resolve().parent / "emoji" / "icons.json"
VS16 = "️"


def load_ids(path: Path = ICONS_PATH) -> dict[str, str]:
    """Fallback emoji (without VS16) -> custom_emoji_id, registered icons only."""
    icons = json.loads(path.read_text(encoding="utf-8"))["icons"]
    return {
        spec["fallback"].replace(VS16, ""): str(spec["custom_emoji_id"])
        for spec in icons.values()
        if spec.get("custom_emoji_id")
    }


def build_pattern(ids: dict[str, str]) -> re.Pattern[str] | None:
    if not ids:
        return None
    emoji = "|".join(re.escape(e) + VS16 + "?" for e in sorted(ids, key=len, reverse=True))
    # Existing <tg-emoji>, <code> and <pre> blocks are matched first and kept as they are.
    return re.compile(rf"<tg-emoji\b.*?</tg-emoji>|<(code|pre)\b.*?</\1>|(?P<emoji>{emoji})", re.S)


def apply_custom_emoji(text: str, ids: dict[str, str], pattern: re.Pattern[str] | None) -> str:
    if not pattern or not text:
        return text

    def wrap(match: re.Match[str]) -> str:
        emoji = match.group("emoji")
        if not emoji:
            return match.group(0)
        return f'<tg-emoji emoji-id="{ids[emoji.replace(VS16, "")]}">{emoji}</tg-emoji>'

    return pattern.sub(wrap, text)


class CustomEmojiMiddleware(BaseRequestMiddleware):
    def __init__(self, ids: dict[str, str] | None = None) -> None:
        self.ids = load_ids() if ids is None else ids
        self.pattern = build_pattern(self.ids)

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        if self.pattern and isinstance(method, (SendMessage, EditMessageText)) and not method.entities:
            parse_mode = method.parse_mode
            if isinstance(parse_mode, Default):
                parse_mode = bot.default[parse_mode.name]
            if isinstance(parse_mode, str) and parse_mode.upper() == "HTML":
                method.text = apply_custom_emoji(method.text, self.ids, self.pattern)
        return await make_request(bot, method)
