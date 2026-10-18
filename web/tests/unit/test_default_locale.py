"""English is the site's default language; the visitor's choices still win."""

from shared import i18n
from web.app.i18n import resolve_locale


def test_english_is_the_default_locale():
    assert i18n.DEFAULT_LOCALE == "en"
    assert i18n.SUPPORTED_LOCALES[0] == "en"


def test_a_missing_key_falls_back_to_english():
    assert i18n.load_translation("xx", "common") == i18n.load_translation("en", "common")


def test_a_visitor_without_preferences_gets_english(app):
    with app.test_request_context("/"):
        assert resolve_locale() == "en"


def test_an_unsupported_browser_language_gets_english(app):
    with app.test_request_context("/", headers={"Accept-Language": "de-DE,de;q=0.9"}):
        assert resolve_locale() == "en"


def test_the_browser_language_is_used_when_supported(app):
    with app.test_request_context("/", headers={"Accept-Language": "uk-UA,uk;q=0.9"}):
        assert resolve_locale() == "uk"


def test_the_language_cookie_wins_over_the_browser(app):
    with app.test_request_context(
        "/", headers={"Accept-Language": "uk", "Cookie": "nosifit_locale=pl"}
    ):
        assert resolve_locale() == "pl"
