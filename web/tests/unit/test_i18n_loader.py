"""shared.i18n reads each translation once and hands out copies."""

import pytest

from shared import i18n

NAMESPACES = sorted({path.stem for path in i18n.TRANSLATIONS_DIR.glob("*/*")})


def read_from_disk(locale, namespace):
    translations = i18n._load_raw_translation(i18n.DEFAULT_LOCALE, namespace)
    if locale != i18n.DEFAULT_LOCALE:
        i18n._merge_translations(translations, i18n._load_raw_translation(locale, namespace))
    return translations


def a_text_key(translations, prefix=""):
    """Dotted path of the first string in the nested translations."""
    for key, value in translations.items():
        if isinstance(value, str):
            return prefix + key
        if isinstance(value, dict):
            found = a_text_key(value, f"{prefix}{key}.")
            if found:
                return found
    return None


def lookup(translations, dotted):
    for part in dotted.split("."):
        translations = translations[part]
    return translations


@pytest.fixture(autouse=True)
def fresh_cache():
    i18n._cached_translation.cache_clear()
    yield
    i18n._cached_translation.cache_clear()


@pytest.mark.parametrize("locale", i18n.SUPPORTED_LOCALES)
@pytest.mark.parametrize("namespace", NAMESPACES)
def test_cached_translations_match_the_files(locale, namespace):
    assert i18n.load_translation(locale, namespace) == read_from_disk(locale, namespace)


def test_files_are_read_once_per_locale_and_namespace(monkeypatch):
    reads = []
    real = i18n._load_raw_translation

    def counting(locale, namespace):
        reads.append((locale, namespace))
        return real(locale, namespace)

    monkeypatch.setattr(i18n, "_load_raw_translation", counting)
    for _ in range(3):
        i18n.get_translation("uk", "common", "anything")
        i18n.load_translation("uk", "common")

    assert sorted(reads) == [("en", "common"), ("uk", "common")]


def test_callers_get_their_own_copy():
    first = i18n.load_translation("uk", "common")
    key = a_text_key(first)
    first.clear()

    assert lookup(i18n.load_translation("uk", "common"), key)
    assert i18n.get_translation("uk", "common", key) != key


def test_an_unsupported_locale_reads_english():
    en = i18n.load_translation("en", "common")
    key = a_text_key(en)

    assert i18n.get_translation("de", "common", key) == lookup(en, key)
    assert i18n.load_translation("de", "common") == en


def test_the_version_changes_with_any_text(tmp_path, monkeypatch):
    from shared import i18n

    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "common.json").write_text('{"a": "one"}', encoding="utf-8")
    monkeypatch.setattr(i18n, "TRANSLATIONS_DIR", tmp_path)
    i18n.translations_version.cache_clear()
    try:
        first = i18n.translations_version()
        (tmp_path / "en" / "common.json").write_text('{"a": "two"}', encoding="utf-8")
        i18n.translations_version.cache_clear()
        assert i18n.translations_version() != first
    finally:
        i18n.translations_version.cache_clear()


def test_versioned_texts_may_be_cached_for_good(client):
    from api.routes.i18n import VERSIONED_CACHE
    from shared.i18n import translations_version

    current = client.get(f"/api/v1/i18n/uk/common?v={translations_version()}")
    assert current.status_code == 200
    assert current.headers["Cache-Control"] == VERSIONED_CACHE

    # No version, or one from an older deploy: the texts may have changed.
    for url in ("/api/v1/i18n/uk/common", "/api/i18n/uk/common?v=0123456789ab"):
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store", url
        assert response.get_json() == current.get_json()
