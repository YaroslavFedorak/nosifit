"""Shared (Redis) rate limiting.

Needs a disposable Redis: TEST_REDIS_URL=redis://localhost:6379/15 (the
database is flushed). Skipped when it is not set.
"""

import os
import threading
import time

import pytest
import redis

from web.app import create_app
from web.app.security import (
    KEY_PREFIX,
    RateLimitUnavailable,
    check_rate_limit_config,
    hit_limit,
)

TEST_REDIS_URL = os.getenv("TEST_REDIS_URL")
UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1/0"
PASSWORD = "password123"

needs_redis = pytest.mark.skipif(not TEST_REDIS_URL, reason="TEST_REDIS_URL is not set")


@pytest.fixture
def redis_client():
    client = redis.Redis.from_url(TEST_REDIS_URL)
    client.flushdb()
    yield client
    client.flushdb()


def make_app(app, redis_url):
    """Another application instance on the same database, like a second
    gunicorn worker or Railway replica."""
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
            "RATELIMIT_REDIS_URL": redis_url,
        }
    )


def wrong_login(client, email="test@example.com"):
    return client.post("/auth/login", data={"email": email, "password": "wrong-password"})


def good_login(client):
    return client.post("/auth/login", data={"email": "test@example.com", "password": PASSWORD})


# --- Configuration -------------------------------------------------------------------


def test_production_without_redis_refuses_to_start():
    with pytest.raises(RuntimeError, match="RATELIMIT_REDIS_URL"):
        check_rate_limit_config({"IS_PRODUCTION": True, "RATELIMIT_ENABLED": True})


def test_production_with_redis_starts():
    check_rate_limit_config(
        {"IS_PRODUCTION": True, "RATELIMIT_REDIS_URL": "redis://default:x@redis.railway.internal:6379"}
    )


def test_local_development_works_without_redis():
    check_rate_limit_config({"IS_PRODUCTION": False})


def test_redis_url_scheme_is_validated():
    with pytest.raises(RuntimeError, match="redis://"):
        check_rate_limit_config({"RATELIMIT_REDIS_URL": "http://example.com"})


# --- Shared counters ---------------------------------------------------------------------


@needs_redis
def test_two_instances_share_one_login_counter(app, user, redis_client):
    worker_1 = make_app(app, TEST_REDIS_URL).test_client()
    worker_2 = make_app(app, TEST_REDIS_URL).test_client()

    # 10 failures allowed per email in total, split across both workers.
    for _ in range(5):
        wrong_login(worker_1)
        wrong_login(worker_2)

    # In-process counters would allow 10 more per worker; Redis does not.
    assert not good_login(worker_1).location.endswith("/dashboard/")
    assert not good_login(worker_2).location.endswith("/dashboard/")


@needs_redis
def test_limit_recovers_after_the_window(app, redis_client):
    instance = make_app(app, TEST_REDIS_URL)

    with instance.test_request_context():
        assert not hit_limit("test-window", "k", 2, 1)
        assert not hit_limit("test-window", "k", 2, 1)
        assert hit_limit("test-window", "k", 2, 1)

        time.sleep(1.2)

        assert not hit_limit("test-window", "k", 2, 1)


@needs_redis
def test_concurrent_requests_cannot_overshoot_the_limit(app, redis_client):
    instances = [make_app(app, TEST_REDIS_URL) for _ in range(2)]
    allowed = []
    lock = threading.Lock()

    def attempt(instance):
        with instance.test_request_context():
            blocked = hit_limit("test-race", "victim@example.com", 10, 60)
        with lock:
            allowed.append(not blocked)

    threads = [
        threading.Thread(target=attempt, args=(instances[i % 2],)) for i in range(40)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(allowed) == 10


@needs_redis
def test_redis_holds_no_personal_data_and_every_key_expires(app, user, redis_client):
    client = make_app(app, TEST_REDIS_URL).test_client()
    wrong_login(client)
    client.post("/auth/reset", data={"email": "test@example.com"})

    keys = [key.decode() for key in redis_client.keys("*")]

    assert keys
    for key in keys:
        assert key.startswith(KEY_PREFIX)
        assert "test@example.com" not in key and "127.0.0.1" not in key
        assert 0 < redis_client.ttl(key) <= 60 * 60
        assert redis_client.get(key).isdigit()


@needs_redis
def test_redis_restart_does_not_break_requests(app, user, redis_client):
    instance = make_app(app, TEST_REDIS_URL)
    client = instance.test_client()
    wrong_login(client)

    # Drop every client connection, as a Redis restart would.
    redis_client.client_kill_filter(_type="normal", skipme=True)

    assert good_login(client).location.endswith("/dashboard/")


# --- Failure: fail closed ------------------------------------------------------------------


@pytest.fixture
def broken_redis_client(app):
    return make_app(app, UNREACHABLE_REDIS_URL).test_client()


def test_login_is_refused_when_redis_is_down(broken_redis_client, user):
    response = good_login(broken_redis_client)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    with broken_redis_client.session_transaction() as session:
        assert "_user_id" not in session


def test_brute_force_does_not_get_through_while_redis_is_down(broken_redis_client, user):
    statuses = {wrong_login(broken_redis_client).status_code for _ in range(30)}

    assert statuses == {503}


@pytest.mark.parametrize(
    "path,data",
    [
        ("/auth/reset", {"email": "test@example.com"}),
        ("/verify/send_code", {"username": "u", "email": "n@example.com", "password": "a-good-password"}),
    ],
)
def test_other_auth_endpoints_fail_closed(broken_redis_client, user, path, data):
    assert broken_redis_client.post(path, data=data).status_code == 503


def test_logged_in_security_actions_fail_closed_with_json(app, user, broken_redis_client):
    with broken_redis_client.session_transaction() as session:
        session["_user_id"] = user.get_id()
        session["_fresh"] = True

    response = broken_redis_client.post(
        "/profile/change_password",
        data={"current_password": PASSWORD, "new_password": "x" * 12, "confirm_password": "x" * 12},
    )

    assert response.status_code == 503
    assert response.json["code"] == "rate_limit_unavailable"


def test_rest_of_the_app_keeps_working_while_redis_is_down(broken_redis_client, user):
    assert broken_redis_client.get("/healthz").status_code == 200
    assert broken_redis_client.get("/auth/login").status_code == 200
    assert broken_redis_client.get("/api/i18n/uk/common").status_code == 200


def test_hit_limit_raises_instead_of_allowing(app):
    instance = make_app(app, UNREACHABLE_REDIS_URL)

    with instance.test_request_context():
        with pytest.raises(RateLimitUnavailable):
            hit_limit("test", "k", 5, 60)


# --- Client identity -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "remote_addr,expected",
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8:1:2:aaaa::1", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:fffe", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
    ],
)
def test_client_ip_groups_ipv6_by_prefix(app, remote_addr, expected):
    from web.app.security import client_ip

    with app.test_request_context(environ_base={"REMOTE_ADDR": remote_addr}):
        assert client_ip() == expected


def test_rotating_ipv6_addresses_shares_one_limit(app, user):
    client = app.test_client()
    statuses = [
        client.post(
            "/auth/reset",
            data={"email": f"x{i}@example.com"},
            environ_base={"REMOTE_ADDR": f"2001:db8:1:2::{i + 1:x}"},
        ).status_code
        for i in range(12)
    ]

    assert statuses.count(429) == 2  # 10 per hour per client
