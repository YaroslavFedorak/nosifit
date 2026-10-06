"""Cross-cutting HTTP security controls.

- Rate limiting for authentication and email endpoints.
- CSRF defence for state-changing requests (Origin / Referer check on top of
  SameSite=Lax cookies).
- Security headers, including a nonce-based Content-Security-Policy.
- JSON bodies with NaN / Infinity are rejected (they pass float range checks).
"""

import json
import logging
import secrets
import threading
import time
from urllib.parse import urlsplit

from flask import abort, current_app, g, jsonify, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from werkzeug.routing import IntegerConverter

logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


# --- Rate limiting -------------------------------------------------------------


class _MemoryBackend:
    """Fixed-window counters in process memory.

    With several gunicorn workers each worker counts separately, so the
    effective limit is ``limit * workers``. Set RATELIMIT_REDIS_URL to share
    counters between workers and instances.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[int, float]] = {}

    def hit(self, key: str, window: int) -> int:
        now = time.monotonic()
        with self._lock:
            if len(self._counters) > 50_000:
                self._counters = {
                    k: v for k, v in self._counters.items() if v[1] > now
                }
            count, reset_at = self._counters.get(key, (0, 0.0))
            if reset_at <= now:
                count, reset_at = 0, now + window
            count += 1
            self._counters[key] = (count, reset_at)
            return count

    def reset(self, key: str) -> None:
        with self._lock:
            self._counters.pop(key, None)


class _RedisBackend:
    def __init__(self, url: str):
        import redis

        self._redis = redis.Redis.from_url(url, socket_timeout=2)

    def hit(self, key: str, window: int) -> int:
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = pipe.execute()
        return int(count)

    def reset(self, key: str) -> None:
        self._redis.delete(key)


def _backend():
    backend = current_app.extensions.get("nosifit_ratelimit")
    if backend is None:
        url = current_app.config.get("RATELIMIT_REDIS_URL")
        backend = _RedisBackend(url) if url else _MemoryBackend()
        current_app.extensions["nosifit_ratelimit"] = backend
    return backend


def _key(scope: str, key) -> str:
    return f"rl:{scope}:{str(key).strip().lower()}"


def hit_limit(scope: str, key, limit: int, window: int) -> bool:
    """Count one attempt; True when ``limit`` attempts per ``window`` s are exceeded."""
    if not current_app.config.get("RATELIMIT_ENABLED", True):
        return False
    try:
        return _backend().hit(_key(scope, key), window) > limit
    except Exception:  # a broken Redis must not take logins down
        logger.exception("Rate limiter backend failed")
        return False


def reset_limit(scope: str, key) -> None:
    try:
        _backend().reset(_key(scope, key))
    except Exception:
        logger.exception("Rate limiter backend failed")


def client_ip() -> str:
    # ProxyFix already replaced remote_addr with the proxy-reported client.
    return request.remote_addr or "unknown"


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


def _content_security_policy(nonce: str) -> str:
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
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
    headers.setdefault("Content-Security-Policy", _content_security_policy(csp_nonce()))
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
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
    # Must run before blueprints add their rules.
    app.url_map.converters["int"] = DbIdConverter

    app.json_provider_class = StrictJSONProvider
    app.json = StrictJSONProvider(app)

    app.before_request(check_csrf)
    app.after_request(set_security_headers)
    app.context_processor(lambda: {"csp_nonce": csp_nonce})

    @app.errorhandler(HTTPException)
    def _http_error(error):
        if request.path.startswith("/api/") or request.is_json:
            return _json_error(error)
        return error

    @app.errorhandler(Exception)
    def _unhandled(error):
        if isinstance(error, HTTPException):
            return _http_error(error)
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({"error": "internal_server_error"}), 500
        return "Internal Server Error", 500

