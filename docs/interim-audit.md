# Interim audit after stage 1

Stage 1 (modular refactoring) is finished. This page records what is
separated, what is not, what the tests cover, and what the later stages
need. Nothing in stage 1 changed deployment, URLs, the database schema or
what users see, apart from the bug fixes listed below.

## What is separated

| Component | State |
|---|---|
| `api` | Every route under `/api/` lives in `api/routes/` (10 blueprints) and is registered by `api.register_api`. No module under `api/` imports `db`, a model or SQLAlchemy: routes validate input, call a `core` service and shape the response. |
| `core` | Business logic and data access in `backend/`. It imports nothing from `web` or `api`. New services from stage 1: `verification_codes`, the rate limiter (`backend/app/utils/rate_limit.py`), `training/catalog_service`, `training/plan_service`, `training/performance_service`, `recovery/training_summary`, plus new methods on the nutrition, habit, session and Telegram services. |
| `shared` | Standard library only: bot request signing, barcode normalisation, the translation files and their loader. |
| `bot` | Talks to the backend only over HTTP. Importing it loads neither Flask, SQLAlchemy nor `backend`. |
| `web` | Pages, templates, static files, sign-in and OAuth flows. |

`web/tests/unit/test_architecture.py` checks every rule above on each test
run, and `web/tests/unit/test_url_map.py` checks that no URL has two views.

### The one known boundary violation

`api/routes/telegram.py` imports `web.app.routes.auth.telegram_session`:
signing in through the bot writes the same Flask-Login session the pages
use. It has to move to a shared auth module before the API can run as its
own service.

*Update:* fixed right after this audit. The helpers now live in the `auth`
package, which both `web` and `api` import, and no known violation is
left.

## What still does database work outside `core`

The sign-in, registration, OAuth and profile forms in `web/app/routes/`
still query and write through the models themselves (about 60 calls in 14
files; most are in `auth/`). They are pages and form posts, not API
endpoints. Moving them is useful but does not block a separate API
service.

JSON endpoints outside `/api/` stay in `web` until API v1 decides whether
each one becomes part of the public API: the `/profile/*` posts,
`/plan/json`, the `/questionnaire/` post, `/verify/send_code` and the
Telegram link confirmation.

## Tests

- 1,138 tests, run on a PostgreSQL schema built by the real Alembic
  migrations, isolated per run. `test_schema_drift` fails if the models and
  the migrations disagree. CI runs them on every pull request, with the
  frontend build and a dependency audit.
- Line coverage, measured at the end of stage 1:

  | Code | Statements | Covered |
  |---|---:|---:|
  | everything | 13,446 | 81% |
  | `api/` | 1,472 | 92% |
  | `backend/app/services/` | 4,910 | 86% |
  | `backend/app/models/` | 565 | 91% |
  | `web/app/routes/` | 1,203 | 87% |
  | `telegram_bot/` | 2,729 | 72% |
  | `backend/app/training/` (older analytics and plan generator) | 1,342 | 60% |

  The least covered code is the older training analytics in
  `backend/app/training/`; it is the first place to add tests before it
  changes.
- Stage 0 and 1 added tests for every API module before it moved: access
  rules (every route needs signing in), other users' data being
  unreachable, validation errors, rate limits, the critical user flows, the
  static asset cache and compression. Each new test was run against the
  old code and the new code.

## Bugs found and fixed on the way

| Bug | Fix |
|---|---|
| Deleting an account answered 500 in production (a dropped `recovery_plans` table was still mapped) | #36 |
| `/pricing` answered 500 | #36 |
| The training day view answered 500 for a malformed date | #50 |

## Doubtful behaviour, documented and left as it is

None of these is a crash. Each one changes what a client sees, so each
needs its own decision rather than a fix hidden in a refactoring.

- The dashboard "today" card always reports 0 for water and habits; the
  values are stubs.
- The injuries and onboarding endpoints treat a JSON body that is not an
  object (a list, a string) as `{}` instead of rejecting it.
- Onboarding accepts free-form values for its choices and can store an
  empty focus.
- `/api/i18n/<locale>/<namespace>`: an unsupported locale falls back to
  Ukrainian, an unknown namespace answers `{}`.
- The nutrition heatmap falls back to the current year when `year` is not
  a number; the recovery heatmap answers 400 for the same input.
- Deleting a missing meal answers `{"error": "Meal not found"}` without the
  `code` the other nutrition errors carry.
- Unauthenticated requests: the recovery API answers 401 JSON, the other
  API modules that need a signed-in user redirect (302) to the sign-in
  page.
- Error bodies come in four shapes: `{"error": message}`,
  `{"error": code, "code": code}`, `{"error": message, "code": code}` and
  `{"error": "invalid_input", "message": message}`.
- `test_rate_limit_redis` flushes the Redis database that `TEST_REDIS_URL`
  points to, so it must be a disposable one (CI uses database 15).

## Left for later on purpose

- No change to deployment, the proxy setup (`ProxyFix`) or the domain.
- No API versioning, no OpenAPI, no background jobs.
- `datetime.utcnow()` and `Query.get()` are deprecated and produce most of
  the test warnings. Replacing them is mechanical but touches stored
  timestamps, so it needs its own pull request with tests.
- Unused images in `web/app/static/img/`: `Nosi_Logo.png` (2 MB),
  `NosiFit_Icon_App1.0.png` (0.9 MB), `logo.svg` and part of the brand
  kit. Pages never load them, so they do not slow anything down; whether
  to keep them as brand sources is the owner's call.

## Next stages

1. **API v1.** One error format and one answer for unauthenticated
   requests (401 JSON), an OpenAPI description, and `/api/v1/` paths next
   to the current ones so the website and the bot can switch over one by
   one.
2. **Shared auth module.** Move the session helpers out of `web`. That
   removes the last boundary violation.
3. **Measure before optimising.** Collect p50/p95 per endpoint from
   production first, then cache what is slow. Candidates: the translation
   files, the dashboard (several requests per page) and the training
   model.

   *Measured right after this audit* (Railway, 7 days, about 8,000
   requests): p50 5–35 ms and p95 30–150 ms overall. One endpoint stood
   out: `/api/dashboard/heatmap` took 0.7–3.6 s, and some page loads were
   given up before it answered. It ran about 1,100 queries per call and
   now runs five. Translations were re-read from disk for every key and
   are now cached per process. What is left above 500 ms waits on outside
   services: sending email (sign-up codes, password reset, account
   deletion) and the barcode lookup. Sending email in the background is
   the case for the `worker` component.
4. **Separate API service.** Only after 1–3, and only with the owner's
   decision on cost. It needs a second Railway service, cookie and CORS
   settings for the API domain, and a plan for the shared session.
