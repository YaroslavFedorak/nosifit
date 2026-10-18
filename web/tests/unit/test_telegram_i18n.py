"""The bot's languages: complete catalogs, language choice, button matching."""

import re
import string
from pathlib import Path

import pytest
from aiogram.types import User as TgUser

from telegram_bot import i18n
from telegram_bot.keyboards.main import MENU_TEXTS, main_menu
from web.tests.security.test_telegram_bot import bot  # noqa: F401

BOT_DIR = Path(i18n.__file__).resolve().parent
_KEY = re.compile(r"""\bt\(\s*["']([a-z_]+(?:\.[a-z_0-9]+)+)["']""")
_FORMATTER = string.Formatter()


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in _FORMATTER.parse(text) if name}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "STORE_PATH", tmp_path / "languages.json")
    monkeypatch.setattr(i18n, "_chosen", {})
    monkeypatch.setattr(i18n, "_detected", {})
    monkeypatch.setattr(i18n, "_loaded", False)
    return tmp_path / "languages.json"


def test_every_language_has_the_same_keys_and_placeholders():
    english = i18n._catalog("en")

    for language in i18n.LANGUAGES:
        catalog = i18n._catalog(language)
        assert set(catalog) == set(english), language
        for key, text in catalog.items():
            assert _placeholders(text) == _placeholders(english[key]), (language, key)


def test_every_key_used_in_the_code_exists():
    english = i18n._catalog("en")
    used = set()
    for path in BOT_DIR.rglob("*.py"):
        used |= set(_KEY.findall(path.read_text(encoding="utf-8")))

    assert used
    assert sorted(used - set(english)) == []


def test_english_is_the_default(store):
    assert i18n.DEFAULT_LANGUAGE == "en"
    assert i18n.language_of(1) == "en"
    assert i18n.language_of(1, "de") == "en"


def test_the_telegram_app_language_is_used_until_one_is_picked(store):
    assert i18n.language_of(1, "uk-UA") == "uk"
    assert i18n.language_of(2, "pl") == "pl"
    assert i18n.language_of(3, "ru") == "ru"

    i18n.set_language(1, "pl")

    assert i18n.language_of(1, "uk-UA") == "pl"


def test_the_picked_language_survives_a_restart(store, monkeypatch):
    i18n.set_language(5, "ru")

    monkeypatch.setattr(i18n, "_chosen", {})
    monkeypatch.setattr(i18n, "_loaded", False)

    assert i18n.language_of(5) == "ru"


def test_an_unknown_language_is_refused(store):
    with pytest.raises(ValueError):
        i18n.set_language(1, "xx")


def test_plural_forms_follow_each_language(monkeypatch):
    forms = {
        "en": {1: "set", 2: "sets", 5: "sets"},
        "uk": {1: "підхід", 2: "підходи", 5: "підходів", 11: "підходів", 21: "підхід"},
        "pl": {1: "seria", 2: "serie", 5: "serii", 12: "serii", 22: "serie"},
        "ru": {1: "подход", 2: "подхода", 5: "подходов", 11: "подходов", 21: "подход"},
    }
    for language, expected in forms.items():
        token = i18n._current.set(language)
        try:
            for count, word in expected.items():
                assert i18n.plural(count, "tr.plural_sets") == word, (language, count)
        finally:
            i18n._current.reset(token)


def test_reply_buttons_are_matched_in_every_language():
    for language in i18n.LANGUAGES:
        token = i18n._current.set(language)
        try:
            buttons = {b.text for row in main_menu(authenticated=True).keyboard for b in row}
        finally:
            i18n._current.reset(token)
        assert buttons <= MENU_TEXTS, language


# --- Through the dispatcher ----------------------------------------------------------------


def _user(user_id: int, language_code: str | None) -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name="Eve", language_code=language_code)


def test_a_new_user_gets_english_unless_the_telegram_app_says_otherwise(bot, store):
    bot.message("/start", user=_user(301, "de"))
    bot.message("/start", user=_user(302, "pl"))

    assert bot.texts()[0] == i18n.translate("en", "start.welcome")
    assert bot.texts()[2] == i18n.translate("pl", "start.welcome")


def test_the_language_command_changes_the_language_for_good(bot, store):
    eve = _user(303, "de")

    bot.message("/language", user=eve)
    assert bot.texts()[-1] == i18n.translate("en", "lang.choose")
    markup = bot.sent()[-1].reply_markup
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == [
        "lang:en",
        "lang:uk",
        "lang:pl",
        "lang:ru",
    ]

    bot.callback("lang:uk", user=eve)
    assert bot.texts()[-1] == i18n.translate("uk", "lang.changed")

    bot.message("/help", user=eve)
    assert bot.texts()[-1] == i18n.translate("uk", "auth.help")
    assert i18n.language_of(303) == "uk"
    assert store.exists()


def test_an_unknown_language_in_a_button_is_ignored(bot, store):
    eve = _user(304, "pl")

    bot.callback("lang:xx", user=eve)

    assert i18n.language_of(304, "pl") == "pl"
    assert not store.exists()
