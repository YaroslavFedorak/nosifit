"""The version of NosiFit: print it, raise it, check it, describe a release.

    python -m web.scripts.version                  # the current version
    python -m web.scripts.version bump minor       # 0.2.0 -> 0.3.0 everywhere, with a CHANGELOG entry to fill in
    python -m web.scripts.version check            # the copies agree and the CHANGELOG describes the version
    python -m web.scripts.version check --base 0.2.0   # ... and it is higher than 0.2.0 (CI, for pull requests)
    python -m web.scripts.version notes [0.2.0]    # that version's CHANGELOG section (the text of its release)

VERSION is the source; a few files must carry the same number (COPIES).
The rules for choosing patch, minor or major are in docs/versioning.md.
Standard library only, so CI runs it without installing anything.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.version import VERSION_FILE, build_number, parse  # noqa: E402

CHANGELOG = ROOT / "CHANGELOG.md"

# File -> how many leading "version" fields carry the app's number. A
# package.json has one; its lock file repeats it once for the root package
# (later "version" fields belong to dependencies and are never touched).
JSON_COPIES = {
    "package.json": 1,
    "package-lock.json": 2,
    "frontend/package.json": 1,
    "frontend/package-lock.json": 2,
}
JSON_VERSION_RE = re.compile(r'("version":\s*")([^"]*)(")')

# The iOS project (XcodeGen): the version and the build number the App Store
# requires (shared.version.build_number). Android computes both from VERSION
# itself (mobile/android/app/build.gradle.kts).
IOS_PROJECT = "mobile/ios/project.yml"
IOS_VERSION_RE = re.compile(r'(MARKETING_VERSION:\s*")([^"]*)(")')
IOS_BUILD_RE = re.compile(r'(CURRENT_PROJECT_VERSION:\s*")([^"]*)(")')

KINDS = ("patch", "minor", "major")


class VersionError(Exception):
    pass


def read_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    try:
        parse(version)
    except ValueError as exc:
        raise VersionError(f"VERSION: {exc}") from None
    return version


def bumped(version: str, kind: str) -> str:
    """The next version: a fix raises PATCH, a feature MINOR, a break MAJOR."""
    major, minor, patch = parse(version)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown kind: {kind!r} (one of {', '.join(KINDS)})")


def is_higher(version: str, base: str) -> bool:
    return parse(version) > parse(base)


# --- The copies ----------------------------------------------------------------------


def _json_versions(text: str, count: int) -> list:
    return [match.group(2) for match in JSON_VERSION_RE.finditer(text)][:count]


def copies(root: Path = ROOT) -> dict:
    """File -> the version numbers it carries now."""
    found = {}
    for name, count in JSON_COPIES.items():
        found[name] = _json_versions((root / name).read_text(encoding="utf-8"), count)
    ios = (root / IOS_PROJECT).read_text(encoding="utf-8")
    found[IOS_PROJECT] = [match.group(2) for match in IOS_VERSION_RE.finditer(ios)]
    found[f"{IOS_PROJECT} (build number)"] = [match.group(2) for match in IOS_BUILD_RE.finditer(ios)]
    return found


def write_copies(version: str, root: Path = ROOT) -> None:
    """Put ``version`` into every copy, changing nothing else in the files."""
    for name, count in JSON_COPIES.items():
        path = root / name
        before = path.read_text(encoding="utf-8")
        after = JSON_VERSION_RE.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", before, count=count)
        _same_json_but_versions(before, after, name)
        path.write_text(after, encoding="utf-8")
    path = root / IOS_PROJECT
    text = IOS_VERSION_RE.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", path.read_text(encoding="utf-8"))
    text = IOS_BUILD_RE.sub(lambda m: f"{m.group(1)}{build_number(version)}{m.group(3)}", text)
    path.write_text(text, encoding="utf-8")


def _same_json_but_versions(before: str, after: str, name: str) -> None:
    """A guard: the edit may change the root package's version, nothing else."""
    old, new = json.loads(before), json.loads(after)
    for data in (old, new):
        data.pop("version", None)
        data.get("packages", {}).get("", {}).pop("version", None)
    if old != new:
        raise VersionError(f"{name}: changing the version would change more than the version")


# --- The changelog -------------------------------------------------------------------


def _section_re(version: str) -> re.Pattern:
    return re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", re.S | re.M)


def notes(version: str, changelog: Path = CHANGELOG) -> str:
    """The CHANGELOG section of ``version``, without its heading."""
    match = _section_re(version).search(changelog.read_text(encoding="utf-8"))
    if not match:
        raise VersionError(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip()


def add_changelog_entry(version: str, changelog: Path = CHANGELOG, today: dt.date | None = None) -> None:
    """A new section on top, for the person releasing to fill in."""
    text = changelog.read_text(encoding="utf-8")
    if _section_re(version).search(text):
        return
    day = (today or dt.date.today()).isoformat()
    entry = f"## [{version}] - {day}\n\n### Added\n\n- \n\n"
    first = text.find("\n## [")
    position = first + 1 if first >= 0 else len(text)
    changelog.write_text(text[:position] + entry + text[position:], encoding="utf-8")


# --- Commands ------------------------------------------------------------------------


def check(base: str | None = None, root: Path = ROOT, changelog: Path = CHANGELOG) -> list:
    """Problems with the version, empty when everything is in order."""
    problems = []
    try:
        version = read_version()
    except VersionError as exc:
        return [str(exc)]

    for name, values in copies(root).items():
        expected = str(build_number(version)) if name.endswith("(build number)") else version
        if not values or any(value != expected for value in values):
            problems.append(f"{name} carries {', '.join(values) or 'nothing'}, expected {expected} for VERSION {version}"
                            " (python -m web.scripts.version bump writes every copy)")

    try:
        text = notes(version, changelog)
        if not re.search(r"^- \S", text, re.M):
            problems.append(f"CHANGELOG.md: the section for {version} lists no change")
    except VersionError as exc:
        problems.append(str(exc))

    if base:
        try:
            if not is_higher(version, base):
                problems.append(
                    f"VERSION {version} is not higher than {base} on the base branch: every merge is a release,"
                    " so raise it (python -m web.scripts.version bump patch|minor|major)"
                )
        except ValueError as exc:
            problems.append(f"base version: {exc}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m web.scripts.version", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    bump = sub.add_parser("bump", help="raise the version in VERSION and every copy")
    bump.add_argument("kind", choices=KINDS)
    checking = sub.add_parser("check", help="exit 1 when the version is not in order")
    checking.add_argument("--base", help="the version on the branch this change goes into")
    described = sub.add_parser("notes", help="print the CHANGELOG section of a version")
    described.add_argument("version", nargs="?")
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            print(read_version())
        elif args.command == "bump":
            new = bumped(read_version(), args.kind)
            VERSION_FILE.write_text(new + "\n", encoding="utf-8")
            write_copies(new)
            add_changelog_entry(new)
            print(f"{new}: now describe the changes in CHANGELOG.md")
        elif args.command == "check":
            problems = check(args.base)
            for problem in problems:
                print(f"error: {problem}", file=sys.stderr)
            if problems:
                return 1
            print(f"{read_version()}: in order")
        elif args.command == "notes":
            print(notes(args.version or read_version()))
    except VersionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
