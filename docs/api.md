# The JSON API

Everything under `/api/` is the JSON API (`api/routes/`, registered by
`api.register_api`). The machine-readable description is
[openapi.json](openapi.json). This page covers what the description cannot
say: versions, errors, authentication, background email and how close the
API is to running as its own service.

## Versions

- `/api/v1/...` is the versioned API. The OpenAPI description uses these
  paths (`servers: /api/v1`).
- The unversioned `/api/...` paths are aliases, kept for the clients that
  already use them (the website's scripts, the Telegram bot). They are a
  second registration of the same blueprints, so they share every view,
  hook and service with v1 and cannot behave differently.
  `web/tests/unit/test_api_v1_contract.py` checks this from the outside:
  the same rules, the same answers for guests and for a signed-in user, the
  same CSRF and Telegram-session rules.
- Compatible changes go into v1: new endpoints, new optional request
  fields, new response fields, new error codes. A client must ignore fields
  it does not know.
- An incompatible change (a field removed or renamed, a different type or
  meaning, a stricter validation that rejects what v1 accepted) needs `/api/v2/`
  next to v1. v1 stays until every known client has moved.
- The unversioned aliases stay as long as v1 does. New clients should call
  `/api/v1/`.

The bot signs the path it calls, so a signature made for `/api/telegram/login`
is not valid on `/api/v1/telegram/login`.

## Errors

Every error under `/api/` is JSON with one shape:

```json
{"code": "meal_not_found", "message": "Meal not found", "error": "Meal not found"}
```

| Field | Meaning |
|---|---|
| `code` | Stable, machine-readable, snake_case. Branch on this. |
| `message` | Human-readable English. Never an exception text, SQL or a stack trace. |
| `details` | Optional object, only where an endpoint has structured data to add. |
| `error` | Kept for older clients. It holds what the endpoint returned there before (sometimes a code, sometimes a message). New clients should not use it. |

Endpoints may still build their own `{"error": ...}` bodies;
`api/errors.py` completes every error response under `/api/` with `code` and
`message`, and the app's error handlers answer unknown URLs, wrong methods,
malformed JSON and unexpected exceptions in the same shape. Pages keep their
HTML errors.

| Status | Typical `code` | When |
|---|---|---|
| 400 | `invalid_input`, `bad_request`, `invalid_category`, `invalid_entry`, ... | The request is malformed or a value is out of range. `message` says which. |
| 401 | `authentication_required` | No valid session. |
| 401 | `session_revoked` | A Telegram session whose Telegram account was disconnected. |
| 401 | `unauthorized` | A bot call with a missing or wrong signature. |
| 403 | `forbidden` | A cross-site write (Origin/Referer), or a premium-only resource. |
| 403 | `telegram_session_scope` | The endpoint is not open to a Telegram session. |
| 404 | `not_found`, `meal_not_found`, `entry_not_found`, ... | Unknown URL or a resource that does not exist or is not the user's. |
| 405 | `method_not_allowed` | The `Allow` header lists the methods that work. |
| 409 | `already_linked`, `email_unavailable` | Telegram registration and linking conflicts. |
| 413 | `payload_too_large` | Bot requests over 4 KB. |
| 429 | `rate_limited`, `too_many_attempts` | Rate limits (Redis-backed, shared by all workers). |
| 500 | `internal_server_error` | Anything unexpected. The details are only in the server log. |
| 503 | `rate_limit_unavailable`, `send_failed`, `unavailable` | Redis, the email service or the configuration is missing. |

No endpoint answers 422 today; validation errors are 400.

## Authentication

| Who | How | Endpoints |
|---|---|---|
| Website | Flask-Login session cookie from signing in on the site | everything except the two rows below |
| Telegram bot | Requests signed with the bot secret (headers `X-NosiFit-Bot-*`); `POST /telegram/login` then gives it an ordinary session cookie, limited to the endpoints the bot needs | `/telegram/*` |
| Anyone | none | `GET /i18n/{locale}/{namespace}`, `GET /injuries/` |

- Without a session, API endpoints answer **401 JSON**. Pages still
  redirect to the sign-in form. (Before, most API endpoints redirected too,
  so a script got the HTML sign-in page with status 200.)
- Writes from a browser must come from the site itself: Origin, or Referer
  when Origin is missing, must be the site's own. This is unchanged and
  applies to `/api/v1/` as well.
- A Telegram session may only use nutrition, the workout logging endpoints
  and exercise search (`auth/telegram_session.py`); the same list applies to
  the v1 paths.

## Background email

Security notices whose failure the user never saw anyway (Telegram
connected, Telegram disconnected, email changed) are queued in the
`email_outbox` table and sent by a thread in each web worker (started by
`gunicorn.conf.py`). See `backend/app/services/email_outbox.py`:

- the queue is PostgreSQL, so a restart or deploy loses nothing;
- failures are retried after 30 s, 2 min, 10 min, 30 min and 2 h, then the
  row is marked `failed` and logged at ERROR;
- a `dedup_key` is queued once, and two workers never take the same row
  (`FOR UPDATE SKIP LOCKED` and a 5-minute lease);
- a worker that dies after the email service accepted a message, but before
  it recorded that, sends it once more after the lease (at-least-once; the
  providers offer no idempotency key);
- logs name the row and its kind, never the address or the text;
- sent rows are deleted after 7 days, failed ones after 30.

`python -m web.scripts.email_outbox` shows the counts and the age of the
oldest unsent email; `--failed` lists the failures, `--send` sends what is due.

Codes and links the user is waiting for (registration and email-change codes,
password reset, account deletion, Telegram disconnect codes, the Telegram
registration code) are still sent in the request. Their pages and the bot
tell the user at once when sending failed, and the registration answers take
the same time whether or not the address has an account; moving them to the
background would change both.

## Could the API run as its own service?

`create_app(pages=False)` builds the API alone. The tests in
`web/tests/unit/test_api_service_readiness.py` show, with real requests:

- no page, sign-in form or bot code is loaded or registered;
- a session cookie issued by the full app (the web service) works on it,
  given the same `SECRET_KEY`;
- 401 without a session, CSRF checks, JSON errors, `/healthz`;
- the bot's link-token endpoint works without the web routes (it used
  `url_for()` on a web page before: a 500 in an API-only app);
- production still refuses to start without the Redis rate-limit store.

Not verified, and needed before a separate deployment:

- **Cookie and domain.** The API on its own host needs the session cookie
  for that host (`SESSION_COOKIE_DOMAIN` covering both, or the API behind
  the same domain under `/api/`). With a different origin the website would
  also need CORS with credentials, and the CSRF Origin check would need the
  site's origin in `TRUSTED_ORIGINS`.
- **One secret, one database, one Redis** shared by both services.
- **Migrations and seeding** stay with one service (today the web service's
  pre-deploy command); the other must not run them.
- **The email outbox worker** runs wherever `gunicorn.conf.py` is used; with
  two services, both would send (safe: the rows are locked), or one could
  leave it out.
- **Telegram link pages** stay on the web service; the API builds links to
  them from `PUBLIC_BASE_URL`.
- **Health and shutdown.** `/healthz` exists in both; gunicorn's graceful
  shutdown also stops the outbox thread (unsent rows go back to the queue).

## Manual action: the Telegram bot's watch paths on Railway

The bot service rebuilds only when files matching its Watch Paths change.
These are set in the Railway dashboard, not in the repository:

- today: `telegram_bot/**`, `requirements.txt`
- the bot also runs code from `shared/` (request signing, barcodes,
  translations), and Railpack picks the Python version from
  `.python-version`.

Railway → project **nosifit** → service **telegram bot** → Settings →
Build → **Watch Paths**: keep the two lines and add

```text
shared/**
.python-version
```

No other local package is imported by the bot (`test_architecture.py`
checks that it imports neither `backend`, `web`, `api` nor `auth`). The web
service has no watch paths, so it rebuilds on every push; leave it so.
