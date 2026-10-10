"""Minimal Open Food Facts client: one product by barcode.

API: ``GET {OFF_BASE_URL}/api/v2/product/{barcode}?fields=…`` (read
operations need no authentication; every app must send its own
User-Agent). Data is licensed under the ODbL 1.0, contents DbCL 1.0; see
web/scripts/nutrition_catalog/SOURCES.md.

Safety:
- only ``OFF_BASE_URL`` is contacted, it must be an Open Food Facts https
  host, the path is built from an already validated digits-only barcode,
  redirects are not followed and no URL from a response is ever fetched;
- connect/read timeouts and a response size cap;
- the response is reduced to the whitelisted fields below before it is
  stored or used, and every value stays untrusted (validated later).

Outcomes: ``found`` / ``not_found`` are confirmed answers; everything else
(timeouts, HTTP errors, rate limits, malformed bodies) raises
``OpenFoodFactsUnavailable`` and must never be cached as "not found".
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests
from flask import current_app

logger = logging.getLogger(__name__)

PROVIDER = "open_food_facts"
ALLOWED_HOSTS = frozenset({
    "world.openfoodfacts.org",
    # Staging, for manual testing against a non-production database.
    "world.openfoodfacts.net",
})
MAX_RESPONSE_BYTES = 512 * 1024
CONNECT_TIMEOUT_SECONDS = 3.05

TEXT_FIELDS = (
    "code",
    "lang",
    "product_name",
    "product_name_uk",
    "product_name_en",
    "product_name_pl",
    "product_name_ru",
    "brands",
    "quantity",
    "product_quantity_unit",
    "serving_size",
    "serving_quantity_unit",
    "nutrition_data_per",
    "no_nutrition_data",
)
NUMBER_FIELDS = ("product_quantity", "serving_quantity")
NUTRIENTS = (
    "energy-kcal",
    "energy-kj",
    "energy",
    "proteins",
    "fat",
    "carbohydrates",
    "fiber",
    "sugars",
    "saturated-fat",
    "salt",
    "sodium",
)
NUTRIENT_SUFFIXES = ("_100g", "_serving")
REQUESTED_FIELDS = ",".join(TEXT_FIELDS + NUMBER_FIELDS + ("nutriments",))
MAX_TEXT_LENGTH = 300


class OpenFoodFactsUnavailable(RuntimeError):
    """No confirmed answer: the lookup must be retried later, not cached."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class OpenFoodFactsAnswer:
    status: str  # "found" | "not_found"
    product: dict | None = None


def _base_url() -> str:
    base = current_app.config.get("OFF_BASE_URL") or "https://world.openfoodfacts.org"
    parts = urlsplit(base)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.path not in ("", "/"):
        # A misconfiguration must not turn into requests to arbitrary hosts.
        raise OpenFoodFactsUnavailable("misconfigured")
    return f"https://{parts.netloc}"


def _clean_text(value):
    if not isinstance(value, str):
        return None
    # Drop control characters; keep the text otherwise as received.
    text = "".join(ch for ch in value if ch.isprintable() or ch == " ")
    return text.strip()[:MAX_TEXT_LENGTH] or None


def _clean_number(value):
    """Numbers (or numeric strings) as given; anything else is dropped.

    Range checks happen in validation, so invalid numbers stay visible as
    invalid rather than disappearing here.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            number = float(value.strip().replace(",", "."))
        except ValueError:
            return value.strip()[:32]  # kept so validation can report it
    else:
        return None
    if not math.isfinite(number):
        return "invalid"
    return number


def extract_product(raw: dict) -> dict:
    """The whitelisted subset of an Open Food Facts product object."""
    product = {}
    for key in TEXT_FIELDS:
        value = _clean_text(raw.get(key))
        if value is not None:
            product[key] = value
    for key in NUMBER_FIELDS:
        value = _clean_number(raw.get(key))
        if value is not None:
            product[key] = value

    nutriments = raw.get("nutriments")
    cleaned = {}
    if isinstance(nutriments, dict):
        for name in NUTRIENTS:
            for suffix in NUTRIENT_SUFFIXES:
                key = name + suffix
                if key in nutriments:
                    value = _clean_number(nutriments.get(key))
                    if value is not None:
                        cleaned[key] = value
    product["nutriments"] = cleaned
    return product


def _read_json(response: requests.Response):
    size = 0
    chunks = []
    for chunk in response.iter_content(chunk_size=16384):
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise OpenFoodFactsUnavailable("too_large")
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


def fetch_product(barcode: str, session: requests.Session | None = None) -> OpenFoodFactsAnswer:
    """Ask Open Food Facts about one canonical barcode (digits only)."""
    if not current_app.config.get("OFF_ENABLED", True):
        raise OpenFoodFactsUnavailable("disabled")
    if not (barcode.isdigit() and 8 <= len(barcode) <= 14):
        raise ValueError("barcode must be validated before the lookup")

    url = f"{_base_url()}/api/v2/product/{barcode}"
    timeout = float(current_app.config.get("OFF_TIMEOUT_SECONDS", 5))
    http = session or requests
    try:
        response = http.get(
            url,
            params={"fields": REQUESTED_FIELDS},
            headers={
                "User-Agent": current_app.config.get("OFF_USER_AGENT") or "NosiFit/0.1",
                "Accept": "application/json",
            },
            timeout=(CONNECT_TIMEOUT_SECONDS, timeout),
            allow_redirects=False,
            stream=True,
        )
    except requests.Timeout:
        logger.warning("Open Food Facts timeout")
        raise OpenFoodFactsUnavailable("timeout")
    except requests.RequestException as exc:
        logger.warning("Open Food Facts request failed: %s", type(exc).__name__)
        raise OpenFoodFactsUnavailable("network")

    try:
        status_code = response.status_code
        if status_code in (429, 503):
            # Open Food Facts answers 503 (or 429) when its limits are hit.
            logger.warning("Open Food Facts rate limited (HTTP %s)", status_code)
            raise OpenFoodFactsUnavailable("rate_limited")
        if status_code not in (200, 404):
            logger.warning("Open Food Facts HTTP %s", status_code)
            raise OpenFoodFactsUnavailable("http_error")

        try:
            payload = _read_json(response)
        except requests.RequestException:
            raise OpenFoodFactsUnavailable("network")
    finally:
        response.close()

    if not isinstance(payload, dict) or payload.get("status") not in (0, 1, "0", "1"):
        # An HTML error page or a truncated body is not "product not found".
        logger.warning("Open Food Facts malformed response (HTTP %s)", status_code)
        raise OpenFoodFactsUnavailable("malformed")

    if str(payload.get("status")) == "0":
        return OpenFoodFactsAnswer("not_found")

    product = payload.get("product")
    if status_code != 200 or not isinstance(product, dict):
        raise OpenFoodFactsUnavailable("malformed")
    return OpenFoodFactsAnswer("found", extract_product(product))
