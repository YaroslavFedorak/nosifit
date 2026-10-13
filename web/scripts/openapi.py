"""Write docs/openapi.json from the registered API routes.

    python -m web.scripts.openapi

Run it after changing an API route or api/openapi_docs.py; the test suite
fails while the committed file is out of date.
"""

import json
from pathlib import Path

from api.openapi import build_spec
from web.app import create_app

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def render(app) -> str:
    return json.dumps(build_spec(app), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    # The description needs the URL map only; no database connection is made.
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://openapi@localhost/unused"},
        pages=False,
    )
    OUTPUT.write_text(render(app), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
