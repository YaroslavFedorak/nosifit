"""Languages of the bot.

Texts live in ``telegram_bot/locales/<language>/*.json`` (flat keys, ``{name}``
placeholders). A missing key falls back to English, then to the key itself.

The language of the current update is kept in a context variable set by
``LanguageMiddleware``, so handlers and keyboards call ``t("key")`` without
passing the user around. Which language a user gets:

1. the one picked with /language (kept in a small JSON file, so it survives
   restarts and redeploys while the file does);
2. else the language of the Telegram app (``language_code``);
3. else English.
"""

import json
import logging
import os
import tempfile
import threading
from collections.abc import Awaitable, Callable, Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from aiogram import BaseMiddleware

logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": "English",
    "uk": "Українська",
    "pl": "Polski",
    "ru": "Русский",
}
DEFAULT_LANGUAGE = "en"

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
STORE_PATH = Path(
    os.getenv("TELEGRAM_BOT_LANGUAGES_FILE")
    or Path(__file__).resolve().parent / "data" / "languages.json"
)

_current: ContextVar[str] = ContextVar("bot_language", default=DEFAULT_LANGUAGE)

_catalogs: dict[str, dict[str, str]] = {}
_lock = threading.Lock()
# Picked with /language (persisted) and seen in the Telegram app (memory only).
_chosen: dict[int, str] = {}
_detected: dict[int, str] = {}
_loaded = False


def _catalog(language: str) -> dict[str, str]:
    catalog = _catalogs.get(language)
    if catalog is None:
        catalog = {}
        directory = LOCALES_DIR / language
        for path in sorted(directory.glob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                catalog.update(json.load(file))
        _catalogs[language] = catalog
    return catalog


def normalize(code: str | None) -> str | None:
    """"uk-UA" -> "uk"; None when the bot has no such language."""
    short = (code or "").strip().lower().replace("_", "-").split("-")[0]
    return short if short in LANGUAGES else None


def current_language() -> str:
    return _current.get()


def translate(language: str, key: str, **params: Any) -> str:
    text = _catalog(language).get(key)
    if text is None:
        text = _catalog(DEFAULT_LANGUAGE).get(key, key)
    return text.format(**params) if params else text


def t(key: str, **params: Any) -> str:
    """Text for the language of the current update."""
    return translate(_current.get(), key, **params)


def plural(count: int, key: str) -> str:
    """The form of a word for ``count``: the text is "one|few|many"
    ("set|sets|sets" in English, where few and many are the same)."""
    one, few, many = t(key).split("|")
    if _current.get() == "en":
        return one if count == 1 else many
    if count == 1 if _current.get() == "pl" else count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def variants(key: str) -> frozenset[str]:
    """The text in every language: a reply button is matched by what the user
    pressed, and that can be a button sent before they changed language."""
    return frozenset(translate(language, key) for language in LANGUAGES)


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, ValueError):
        logger.warning("Language preferences could not be read: %s", STORE_PATH)
        return
    for user_id, language in (data if isinstance(data, dict) else {}).items():
        if user_id.isdigit() and language in LANGUAGES:
            _chosen[int(user_id)] = language


def _save() -> None:
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=STORE_PATH.parent, delete=False
        ) as file:
            json.dump({str(uid): lang for uid, lang in _chosen.items()}, file)
        os.replace(file.name, STORE_PATH)
    except OSError:
        logger.warning("Language preferences could not be saved: %s", STORE_PATH)


def language_of(user_id: int, telegram_code: str | None = None) -> str:
    with _lock:
        _load()
        if telegram_code is not None:
            detected = normalize(telegram_code)
            if detected:
                _detected[user_id] = detected
            else:
                _detected.pop(user_id, None)
        return _chosen.get(user_id) or _detected.get(user_id) or DEFAULT_LANGUAGE


def set_language(user_id: int, language: str) -> None:
    """Remember the user's pick and use it for the rest of this update."""
    if language not in LANGUAGES:
        raise ValueError(language)
    with _lock:
        _load()
        _chosen[user_id] = language
        _save()
    _current.set(language)


class LanguageMiddleware(BaseMiddleware):
    """Sets the language of the update before any handler or filter runs."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is not None:
            _current.set(language_of(user.id, user.language_code))
        return await handler(event, data)


class Texts(Mapping):
    """Texts by key (``prefix.key``) that follow the language of the current update."""

    def __init__(self, prefix: str, keys: tuple[str, ...]):
        self._prefix = prefix
        self._keys = keys

    def __getitem__(self, key: str) -> str:
        if key not in self._keys:
            raise KeyError(key)
        return t(f"{self._prefix}.{key}")

    def __iter__(self):
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)
