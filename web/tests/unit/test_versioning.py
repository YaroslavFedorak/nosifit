"""One version number for the whole product (docs/versioning.md)."""

import datetime as dt
import json
import shutil

import pytest

from shared.version import app_version, build_number, parse, release_stage
from web.scripts import version as tool


def test_the_repository_version_is_in_order():
    """VERSION is MAJOR.MINOR.PATCH, every copy agrees and the CHANGELOG describes it."""
    assert tool.check() == []
    assert tool.read_version() == app_version()


@pytest.mark.parametrize(
    ("version", "kind", "expected"),
    [
        ("0.2.0", "patch", "0.2.1"),
        ("0.2.9", "minor", "0.3.0"),
        ("0.9.4", "minor", "0.10.0"),
        ("0.12.3", "major", "1.0.0"),
        ("1.4.12", "patch", "1.4.13"),
    ],
)
def test_bumping(version, kind, expected):
    assert tool.bumped(version, kind) == expected


def test_versions_compare_as_numbers_not_text():
    assert tool.is_higher("0.10.0", "0.9.9")
    assert not tool.is_higher("0.2.0", "0.2.0")
    assert not tool.is_higher("0.1.9", "0.2.0")


@pytest.mark.parametrize("bad", ["", "1.0", "v1.0.0", "1.0.0-beta", "01.2.3", "1.2.3.4"])
def test_only_plain_semver_is_a_version(bad):
    with pytest.raises(ValueError):
        parse(bad)


def test_a_pull_request_must_raise_the_version():
    current = app_version()
    assert tool.check(base="0.0.1") == []
    problems = tool.check(base=current)
    assert len(problems) == 1 and "not higher" in problems[0]


def test_the_stores_build_number_grows_with_the_version():
    assert build_number("0.2.0") == 2000
    assert build_number("1.4.12") == 1004012
    assert build_number("0.10.0") > build_number("0.9.999")


def test_the_beta_is_every_version_before_one():
    assert release_stage("0.2.0") == "beta"
    assert release_stage("1.0.0") is None


def test_android_packs_the_number_the_same_way():
    gradle = (tool.ROOT / "mobile/android/app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'rootProject.file("../../VERSION")' in gradle
    assert "major * 1_000_000 + minor * 1_000 + patch" in gradle


@pytest.fixture
def repo_copy(tmp_path):
    for name in [*tool.JSON_COPIES, tool.IOS_PROJECT]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(tool.ROOT / name, target)
    return tmp_path


def test_a_bump_writes_every_copy_and_nothing_else(repo_copy):
    before = {name: json.loads((repo_copy / name).read_text(encoding="utf-8")) for name in tool.JSON_COPIES}
    tool.write_copies("9.8.7", root=repo_copy)

    found = tool.copies(repo_copy)
    assert found[tool.IOS_PROJECT] == ["9.8.7"]
    assert found[f"{tool.IOS_PROJECT} (build number)"] == ["9008007"]
    for name in tool.JSON_COPIES:
        assert set(found[name]) == {"9.8.7"}, name
        after = json.loads((repo_copy / name).read_text(encoding="utf-8"))
        assert after["version"] == "9.8.7"
        # Dependencies keep their own versions.
        for data in (before[name], after):
            data.pop("version")
            data.get("packages", {}).get("", {}).pop("version", None)
        assert after == before[name], name


def test_a_new_version_gets_a_changelog_section_on_top(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\nIntro.\n\n## [0.2.0] - 2026-11-27\n\n### Added\n\n- Old thing.\n", encoding="utf-8")
    tool.add_changelog_entry("0.3.0", changelog, today=dt.date(2026, 12, 1))
    text = changelog.read_text(encoding="utf-8")
    assert text.index("## [0.3.0] - 2026-12-01") < text.index("## [0.2.0]")
    assert tool.notes("0.2.0", changelog) == "### Added\n\n- Old thing."
    # An empty entry does not pass the check until it lists a change.
    assert tool.notes("0.3.0", changelog) == "### Added\n\n-"


def test_release_notes_come_from_the_changelog():
    notes = tool.notes(app_version())
    assert notes.startswith("### ")
    with pytest.raises(tool.VersionError):
        tool.notes("99.0.0")


def test_the_cli(capsys):
    assert tool.main([]) == 0
    assert capsys.readouterr().out.strip() == app_version()
    assert tool.main(["check"]) == 0
    assert tool.main(["check", "--base", app_version()]) == 1


# --- Where the version shows ------------------------------------------------------------


def test_the_health_check_reports_the_version(client, monkeypatch):
    assert client.get("/healthz").get_json() == {"status": "ok", "version": app_version()}
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "3de09b19cbdd4bbe02737619944377a6d0231266")
    assert client.get("/healthz").get_json()["commit"] == "3de09b1"


def test_api_responses_name_the_release(client):
    for path in ("/api/v1/i18n/en/common", "/api/i18n/en/common", "/api/v1/dashboard/today"):
        assert client.get(path).headers["NosiFit-Version"] == app_version(), path
    assert "NosiFit-Version" not in client.get("/auth/login").headers


def test_open_food_facts_sees_the_version(app, monkeypatch):
    from backend.config import Config

    if not app.config["OFF_USER_AGENT"].startswith("NosiFit/"):
        pytest.skip("OFF_USER_AGENT is set in the environment")
    assert app.config["OFF_USER_AGENT"].startswith(f"NosiFit/{app_version()} ")
    assert Config.OFF_USER_AGENT == app.config["OFF_USER_AGENT"]
