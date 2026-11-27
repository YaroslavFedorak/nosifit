"""The chunks of the React build one page needs, read from Vite's manifest.

Without help the browser finds the code one file after another: the HTML
names app.js, app.js names the shared chunk, and only when that code runs
does it ask for the page's own chunk and its language. Each step is a round
trip, which on a phone network costs more than the files themselves. The
shell lists those chunks up front (``<link rel="modulepreload">``), so they
load together with app.js.

Only code is listed. Measured on a throttled phone profile (4x CPU, 150 ms,
1.6 Mbps), preloading the fonts or the server texts as well made the page
appear later: they took bandwidth and connections from the code that has
to run before anything is shown. The fonts still come from the stylesheet
as text needs them, and the server texts from the HTTP cache once fetched.

The manifest is web/app/static/app/.vite/manifest.json, written by
``npm --prefix frontend run build`` (``build.manifest`` in vite.config.ts).
Without it the page still works, it only loads in more steps.
"""

import json
import os
from functools import lru_cache

MANIFEST = os.path.join("app", ".vite", "manifest.json")
ENTRY = "src/main.tsx"

# Route name -> the page module App.tsx loads for it.
PAGE_MODULES = {
    "welcome": "src/pages/Landing.tsx",
    "how-it-works": "src/pages/HowItWorks.tsx",
    "dashboard": "src/pages/Dashboard.tsx",
    "nutrition": "src/pages/Nutrition.tsx",
    "training": "src/pages/Training.tsx",
    "recovery": "src/pages/Recovery.tsx",
    "profile": "src/pages/Profile.tsx",
    "settings": "src/pages/Settings.tsx",
}

# frontend/src/i18n/index.tsx loads exactly one of these before the first render.
DICTIONARIES = {
    "en": "src/i18n/en.ts",
    "uk": "src/i18n/uk.ts",
    "pl": "src/i18n/pl.ts",
    "ru": "src/i18n/ru.ts",
}


@lru_cache(maxsize=4)
def _manifest(static_folder: str, asset_version: str) -> dict:
    """The manifest of the build this process serves (the asset version
    changes with every build, so a new build is read after a restart)."""
    try:
        with open(os.path.join(static_folder, MANIFEST), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _chunks(manifest: dict, keys) -> list:
    """The files of ``keys`` and of everything they import statically, in
    a stable order, without the entry (the page loads it with <script>)."""
    files = []
    seen = {ENTRY}
    stack = list(reversed(keys))
    while stack:
        key = stack.pop()
        if key in seen or key not in manifest:
            continue
        seen.add(key)
        chunk = manifest[key]
        if isinstance(chunk.get("file"), str):
            files.append(chunk["file"])
        stack.extend(reversed([name for name in chunk.get("imports", ()) if isinstance(name, str)]))
    return files


def page_chunks(static_folder: str, asset_version: str, page: str, locale: str) -> list:
    """Chunk files (relative to the build folder ``app/``) to modulepreload:
    what app.js imports, the page's module and the page's dictionary."""
    manifest = _manifest(static_folder, asset_version)
    if ENTRY not in manifest:
        return []

    keys = list(manifest[ENTRY].get("imports", ()))
    if page in PAGE_MODULES:
        keys.append(PAGE_MODULES[page])
    keys.append(DICTIONARIES.get(locale, DICTIONARIES["en"]))
    return _chunks(manifest, keys)
