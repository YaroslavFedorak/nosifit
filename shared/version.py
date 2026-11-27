"""The version of NosiFit: one number for the website, the API and the apps.

It lives in the VERSION file at the root of the repository and follows
Semantic Versioning, MAJOR.MINOR.PATCH (docs/versioning.md). While MAJOR
is 0 the product is in beta; 1.0.0 is the public launch.

Standard library only: the bot and the scripts read it too.
"""

import os
import re
from functools import lru_cache
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse(version: str) -> tuple[int, int, int]:
    """``"0.2.1"`` -> ``(0, 2, 1)``; ValueError for anything else."""
    match = SEMVER_RE.match(version.strip())
    if not match:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


@lru_cache(maxsize=1)
def app_version() -> str:
    """The version this process runs (read once; a deploy restarts it)."""
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    parse(version)
    return version


def build_number(version: str) -> int:
    """The always-growing integer the app stores ask for besides the version:
    0.2.0 -> 2000, 1.4.12 -> 1004012 (each part below 1000)."""
    major, minor, patch = parse(version)
    return major * 1_000_000 + minor * 1_000 + patch


def release_stage(version: str | None = None) -> str | None:
    """``"beta"`` before 1.0.0, ``None`` from the public launch on."""
    return "beta" if parse(version or app_version())[0] == 0 else None


def deployed_commit() -> str | None:
    """The short commit hash Railway deployed, when it says so."""
    sha = (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "").strip()
    return sha[:7] or None
