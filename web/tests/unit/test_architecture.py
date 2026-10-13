"""Module boundaries (docs/architecture.md), checked on every test run.

Imports are read from the source, so a forbidden dependency fails here even
when it sits inside a function. Known violations are listed explicitly:
a new one fails, and fixing a listed one fails until it leaves the list.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

FRAMEWORK = {"flask", "flask_login", "flask_sqlalchemy", "flask_migrate", "flask_mail", "sqlalchemy", "alembic"}

# API blueprints whose route modules still live in web/app/routes; each
# leaves this list when its module moves into api/routes.
API_STILL_IN_WEB = {
    "dashboard_api",
    "nutrition_api",
    "recovery",
    "telegram_api",
    "training_api",
    "training_dashboard_api",
}

# api -> web, to be removed when translation loading moves out of web
# (the page templates use the same loader and files).
KNOWN_API_TO_WEB = {
    ("api/routes/i18n.py", "web.app.i18n.locale"),
}



def imports_of(package):
    """(file, imported module) for every absolute import under ``package``."""
    found = set()
    for path in sorted((ROOT / package).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update((relative, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add((relative, node.module))
    return found


def top(module):
    return module.split(".")[0]


def test_shared_uses_only_the_standard_library():
    outside = {
        (path, module)
        for path, module in imports_of("shared")
        if top(module) not in sys.stdlib_module_names and top(module) not in {"shared", "__future__"}
    }
    assert outside == set()


def test_bot_reaches_the_backend_only_through_the_http_api():
    forbidden = {"backend", "web"} | FRAMEWORK
    offending = {(path, module) for path, module in imports_of("telegram_bot") if top(module) in forbidden}
    assert offending == set()


def test_importing_the_bot_loads_no_backend_or_framework():
    """Also catches indirect loading through package __init__ files."""
    script = (
        "import importlib, pkgutil, sys, telegram_bot\n"
        "for m in pkgutil.walk_packages(telegram_bot.__path__, 'telegram_bot.'):\n"
        "    importlib.import_module(m.name)\n"
        f"heavy = {sorted(FRAMEWORK | {'backend', 'web'})!r}\n"
        "print(sorted({n.split('.')[0] for n in sys.modules} & set(heavy)))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_core_does_not_depend_on_the_web_layer():
    to_web = {(path, module) for path, module in imports_of("backend") if top(module) == "web"}
    assert to_web == set()


def test_everything_under_api_is_registered_by_the_api_package(app):
    """New JSON endpoints go under /api/ and into api.register_api; pages
    and form posts stay in web."""
    from api import api_blueprints

    api_names = {blueprint.name for blueprint in api_blueprints()}
    misplaced = []
    for rule in app.url_map.iter_rules():
        blueprint = rule.endpoint.rpartition(".")[0]
        if rule.rule.startswith("/api/") != (blueprint in api_names):
            misplaced.append((rule.rule, rule.endpoint))
    assert misplaced == []


def test_api_route_modules_live_in_the_api_package():
    from api import api_blueprints

    in_web = {bp.name for bp in api_blueprints() if not bp.import_name.startswith("api.routes.")}
    assert in_web == API_STILL_IN_WEB


def test_api_route_modules_do_not_import_the_web_layer():
    to_web = {(path, module) for path, module in imports_of("api/routes") if top(module) == "web"}
    assert to_web == KNOWN_API_TO_WEB
