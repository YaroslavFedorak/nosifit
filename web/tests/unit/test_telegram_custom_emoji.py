"""Custom emoji middleware: wraps registered fallback emoji, leaves the rest alone."""

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import SendMessage

from telegram_bot.custom_emoji import (
    CustomEmojiMiddleware,
    apply_custom_emoji,
    build_pattern,
    load_ids,
)

IDS = {"🔥": "111", "🍽": "222"}


def _apply(text, ids=IDS):
    return apply_custom_emoji(text, ids, build_pattern(ids))


def test_wraps_registered_emoji_and_keeps_others():
    assert _apply("🔥 1840 ккал · 🥩 96 г") == '<tg-emoji emoji-id="111">🔥</tg-emoji> 1840 ккал · 🥩 96 г'


def test_matches_with_and_without_variation_selector():
    assert _apply("🍽️ <b>Обід</b>") == '<tg-emoji emoji-id="222">🍽️</tg-emoji> <b>Обід</b>'
    assert _apply("🍽 <b>Обід</b>") == '<tg-emoji emoji-id="222">🍽</tg-emoji> <b>Обід</b>'


def test_skips_code_pre_and_existing_tags():
    text = '<code>🔥</code> <pre>🔥</pre> <tg-emoji emoji-id="9">🔥</tg-emoji>'
    assert _apply(text) == text


def test_no_ids_means_no_change():
    assert _apply("🔥 1840 ккал", {}) == "🔥 1840 ккал"


def test_repo_icons_json_has_no_ids_yet_and_loads():
    # Only real IDs from a registered pack may ever appear here.
    assert all(v.isdigit() for v in load_ids().values())


def _run(method, bot):
    sent = []

    async def make_request(b, m):
        sent.append(m)
        return None

    asyncio.run(CustomEmojiMiddleware(IDS)(make_request, bot, method))
    return sent[0]


def test_middleware_uses_bot_default_html():
    bot = Bot("1:a", default=DefaultBotProperties(parse_mode="HTML"))
    sent = _run(SendMessage(chat_id=1, text="🔥 ккал"), bot)
    assert sent.text == '<tg-emoji emoji-id="111">🔥</tg-emoji> ккал'


def test_middleware_skips_plain_text_messages():
    bot = Bot("1:a", default=DefaultBotProperties(parse_mode="HTML"))
    sent = _run(SendMessage(chat_id=1, text="🔥 ккал", parse_mode=None), bot)
    assert sent.text == "🔥 ккал"
