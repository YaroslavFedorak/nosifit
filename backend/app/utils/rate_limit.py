"""Rate limiting shared by the web pages, the API and core services.

Counters live in Redis (RATELIMIT_REDIS_URL) so every gunicorn worker and
every instance shares them. Production refuses to start without Redis (see
check_rate_limit_config). Locally and in tests an in-process backend is used.

Only HMACs of the identifiers (email, IP, user id) and integers are stored:
no passwords, codes, tokens or readable personal data.

Fail closed: when Redis is unreachable a rate-limited (security-sensitive)
request gets 503 instead of running unlimited. Endpoints without a limit
never touch Redis and keep working.

Request-dependent helpers (client_ip, the 429 response) stay in
web.app.security.
"""

import hashlib
import hmac
import logging
import threading
import time

from flask import current_app

logger = logging.getLogger(__name__)

KEY_PREFIX = "nosifit:rl:"

# INCR and the expiry in one atomic step: concurrent requests in different
# workers can neither skip the TTL nor read a stale count.
_HIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 or redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class RateLimitUnavailable(RuntimeError):
    """The shared rate-limit storage could not be reached."""


class _MemoryBackend:
    """Fixed-window counters in process memory: development and tests only.

    Each gunicorn worker would count separately, so production requires Redis.
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
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        self._redis = redis.Redis.from_url(
            url,
            # Short timeouts: a hung Redis must turn into a quick 503, not
            # tie up gunicorn threads.
            socket_timeout=1,
            socket_connect_timeout=1,
            # One immediate retry covers a dropped pooled connection after a
            # Redis restart; a real outage still fails fast.
            retry=Retry(NoBackoff(), 1),
            retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            health_check_interval=30,
        )
        self._hit = self._redis.register_script(_HIT_SCRIPT)

    def hit(self, key: str, window: int) -> int:
        return int(self._hit(keys=[key], args=[int(window)]))

    def reset(self, key: str) -> None:
        self._redis.delete(key)

    def ping(self) -> bool:
        return bool(self._redis.ping())


def _backend():
    backend = current_app.extensions.get("nosifit_ratelimit")
    if backend is None:
        url = current_app.config.get("RATELIMIT_REDIS_URL")
        backend = _RedisBackend(url) if url else _MemoryBackend()
        current_app.extensions["nosifit_ratelimit"] = backend
    return backend


def _key(scope: str, key) -> str:
    identifier = str(key).strip().lower().encode()
    secret = (current_app.config.get("SECRET_KEY") or "").encode()
    digest = hmac.new(secret, identifier, hashlib.sha256).hexdigest()[:32]
    return f"{KEY_PREFIX}{scope}:{digest}"


def hit_limit(scope: str, key, limit: int, window: int) -> bool:
    """Count one attempt; True when ``limit`` attempts per ``window`` s are exceeded.

    Raises RateLimitUnavailable when the storage is down; the error handler
    answers 503, so a Redis outage never means unlimited attempts.
    """
    if not current_app.config.get("RATELIMIT_ENABLED", True):
        return False
    try:
        return _backend().hit(_key(scope, key), window) > limit
    except Exception as exc:
        logger.error("Rate limit storage unavailable (%s): %s", scope, type(exc).__name__)
        raise RateLimitUnavailable(scope) from exc


def reset_limit(scope: str, key) -> None:
    # Clearing a counter early is a convenience; if it fails the counter just
    # expires on its own.
    try:
        _backend().reset(_key(scope, key))
    except Exception as exc:
        logger.warning("Could not reset rate limit (%s): %s", scope, type(exc).__name__)


def check_rate_limit_config(config) -> None:
    """Fail fast instead of silently running per-process limits in production."""
    url = config.get("RATELIMIT_REDIS_URL")
    if url and not url.startswith(("redis://", "rediss://", "unix://")):
        raise RuntimeError("RATELIMIT_REDIS_URL must be a redis://, rediss:// or unix:// URL")

    if (
        config.get("IS_PRODUCTION")
        and not config.get("TESTING")
        and config.get("RATELIMIT_ENABLED", True)
        and not url
    ):
        raise RuntimeError(
            "RATELIMIT_REDIS_URL is not set. Production needs Redis so login, "
            "password-reset and code limits are shared by all gunicorn workers "
            "and instances. On Railway add a Redis service and set "
            "RATELIMIT_REDIS_URL=${{Redis.REDIS_URL}} on the web service."
        )
