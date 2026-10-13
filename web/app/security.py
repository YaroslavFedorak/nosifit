"""Cross-cutting HTTP security controls.

- Rate limiting for authentication and email endpoints.
- CSRF defence for state-changing requests (Origin / Referer check on top of
  SameSite=Lax cookies).
- Security headers, including a nonce-based Content-Security-Policy.
- JSON bodies with NaN / Infinity are rejected (they pass float range checks).
"""

import ipaddress
import json
import secrets
from urllib.parse import urlsplit

from flask import abort, current_app, g, jsonify, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from werkzeug.routing import IntegerConverter

# The limiter lives in core so services use it without importing the web
# layer; re-exported here for the routes that already import it from here.
from backend.app.utils.rate_limit import (  # noqa: F401
    KEY_PREFIX,
    RateLimitUnavailable,
    check_rate_limit_config,
    hit_limit,
    reset_limit,
)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


# --- Rate limiting -------------------------------------------------------------
#
# The counters are in backend/app/utils/rate_limit.py; the helpers below
# depend on the request.


def check_telegram_config(config) -> None:
    """A short bot secret would make the bot's signatures guessable."""
    from backend.app.utils.bot_signature import MIN_SECRET_LENGTH

    secret = config.get("TELEGRAM_BOT_API_SECRET")
    if secret and len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"TELEGRAM_BOT_API_SECRET must be at least {MIN_SECRET_LENGTH} characters "
            "(python -c \"import secrets; print(secrets.token_hex(32))\")"
        )


def client_ip() -> str:
    """Rate-limit identity of the client.

    ProxyFix already replaced remote_addr with the proxy-reported client.
    IPv6 is grouped by /64: one customer usually gets a whole /64, so
    counting single addresses would let them rotate through 2**64 of them.
    """
    raw = request.remote_addr or "unknown"
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        return raw
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


def too_many_requests(message="Too many requests. Try again later."):
    if request.path.startswith("/api/") or request.is_json:
        response = jsonify({"error": message, "code": "rate_limited"})
    else:
        response = current_app.response_class(message, mimetype="text/plain")
    response.status_code = 429
    return response


# --- CSRF ----------------------------------------------------------------------


def _same_origin(url: str) -> bool:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return False
    origin = f"{parts.scheme}://{parts.netloc}".lower()
    allowed = {request.host_url.rstrip("/").lower()}
    allowed.update(
        o.strip().rstrip("/").lower()
        for o in current_app.config.get("TRUSTED_ORIGINS", ())
        if o.strip()
    )
    return origin in allowed


def check_csrf():
    """Reject cross-site state-changing requests.

    Browsers send Origin on every cross-origin POST/PUT/PATCH/DELETE (and
    Referer when Origin is missing). Clients without either header (the
    Telegram bot, curl) are not browsers, so they cannot carry a victim's
    cookies and are let through.
    """
    if request.method in SAFE_METHODS:
        return None

    origin = request.headers.get("Origin")
    if origin is not None:
        if origin == "null" or not _same_origin(origin):
            abort(403, description="Cross-site request blocked")
        return None

    referer = request.headers.get("Referer")
    if referer and not _same_origin(referer):
        abort(403, description="Cross-site request blocked")
    return None


# --- Security headers ------------------------------------------------------------


def csp_nonce() -> str:
    nonce = getattr(g, "csp_nonce", None)
    if nonce is None:
        nonce = g.csp_nonce = secrets.token_urlsafe(16)
    return nonce


_SCANNER_FLAG = "nosifit.barcode_scanner"


def allow_barcode_scanner() -> None:
    """Lets the current page use the camera and WebAssembly.

    Only pages with the food picker call this (nutrition, dashboard): the
    barcode scanner reads camera frames and, without a native
    BarcodeDetector, decodes them with the self-hosted zxing WebAssembly
    module. Frames never leave the browser. Every other page keeps
    ``camera=()`` and a CSP without WebAssembly. The flag lives on the
    request itself, so it can never carry over to another response.
    """
    request.environ[_SCANNER_FLAG] = True


def _content_security_policy(nonce: str, wasm: bool = False) -> str:
    script_src = f"script-src 'self' 'nonce-{nonce}'"
    if wasm:
        # Compiling WebAssembly only; JS eval() stays blocked.
        script_src += " 'wasm-unsafe-eval'"
    return "; ".join(
        [
            "default-src 'self'",
            script_src,
            # style="" attributes and CSSOM changes are used across templates.
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self' https://accounts.google.com https://github.com",
            "frame-ancestors 'none'",
        ]
    )


def set_security_headers(response):
    headers = response.headers
    scanner = bool(request.environ.get(_SCANNER_FLAG))
    headers.setdefault(
        "Content-Security-Policy", _content_security_policy(csp_nonce(), wasm=scanner)
    )
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault(
        "Permissions-Policy",
        f"camera={'(self)' if scanner else '()'}, microphone=(), geolocation=(), payment=(), usb=()",
    )
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if current_app.config.get("IS_PRODUCTION"):
        headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )

    # Personal data must not stay in shared/browser caches.
    if not request.path.startswith("/static/") and "Cache-Control" not in headers:
        headers["Cache-Control"] = "no-store"
    return response


# --- JSON --------------------------------------------------------------------------


def _reject_constant(value):
    raise ValueError(f"{value} is not allowed in JSON")


class StrictJSONProvider(DefaultJSONProvider):
    """Python's json accepts NaN/Infinity, which slip through ``a <= x <= b``."""

    def loads(self, s, **kwargs):
        kwargs.setdefault("parse_constant", _reject_constant)
        return json.loads(s, **kwargs)


# --- Errors ------------------------------------------------------------------------


def _json_error(error: HTTPException):
    response = jsonify({"error": error.description or error.name})
    response.status_code = error.code or 500
    return response


class DbIdConverter(IntegerConverter):
    """``<int:...>`` limited to PostgreSQL INTEGER: larger ids are a 404,
    not a database error."""

    def __init__(self, map, *args, **kwargs):
        kwargs.setdefault("max", 2**31 - 1)
        super().__init__(map, *args, **kwargs)


def init_security(app):
    check_rate_limit_config(app.config)
    check_telegram_config(app.config)

    # Must run before blueprints add their rules.
    app.url_map.converters["int"] = DbIdConverter

    app.json_provider_class = StrictJSONProvider
    app.json = StrictJSONProvider(app)

    app.before_request(check_csrf)
    app.after_request(set_security_headers)
    app.context_processor(lambda: {"csp_nonce": csp_nonce})

    @app.errorhandler(RateLimitUnavailable)
    def _rate_limit_unavailable(error):
        message = "Service temporarily unavailable. Try again shortly."
        # /auth and /verify are HTML forms; the other limited endpoints are
        # JSON APIs called from the profile page.
        if request.path.startswith(("/auth/", "/verify/")) and not request.is_json:
            response = current_app.response_class(message, mimetype="text/plain")
        else:
            response = jsonify({"error": message, "code": "rate_limit_unavailable"})
        response.status_code = 503
        response.headers["Retry-After"] = "30"
        return response

    @app.errorhandler(HTTPException)
    def _http_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return _json_error(error)
        return error

    @app.errorhandler(Exception)
    def _unhandled(error):
        if isinstance(error, HTTPException):
            return _http_error(error)
        if isinstance(error, RateLimitUnavailable):
            return _rate_limit_unavailable(error)
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({"error": "internal_server_error"}), 500
        return "Internal Server Error", 500

