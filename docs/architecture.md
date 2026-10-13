# Architecture

NosiFit is one repository and, for now, two processes: the Flask app
(`web`, pages and JSON API together) and the Telegram bot (`bot`). The code
is being split into modules with clear boundaries so the API can later run
as its own service without rewriting business logic. Until then nothing
about deployment, URLs or behaviour changes.

## Components

| Component | Responsibility | Lives in today |
|---|---|---|
| `core` | Models, business logic, data access, migrations, config | `backend/` |
| `api` | HTTP endpoints: validate the request, call `core`, shape the response | API blueprints under `web/app/routes/` (moving out step by step) |
| `web` | Pages, templates, static files, sign-in and OAuth flows | `web/app/` |
| `bot` | Telegram interface; talks to the backend only through the HTTP API | `telegram_bot/` |
| `shared` | Pure helpers several components need (bot request signing, barcode normalisation) | `shared/` |
| `worker` | Background jobs, once there is a practical need | not yet |

These are responsibilities, not processes. All of them except `bot` run
inside the same Flask app today.

## Dependency rules

An arrow means "may import".

```text
web ──► core ◄── api
 │        │       │
 └──► shared ◄────┘
         ▲
bot ─────┘        (bot reaches core only over HTTP)
```

- `shared` uses the standard library only. Importing it never loads Flask,
  SQLAlchemy or the models.
- `bot` imports neither `backend`, `web`, Flask nor SQLAlchemy, directly or
  through a package `__init__`.
- `core` does not import `web` (or `api`). It knows nothing about requests,
  templates or sessions.
- `api` and `web` do not import each other's route modules. Logic both need
  belongs in `core`.

`web/tests/unit/test_architecture.py` checks these rules on every test run.
Known violations are listed in that file and are removed as they are fixed:

| Violation | Plan |
|---|---|
| `core` → `web.app.security` (rate limiting) in `barcode_service.py` and `utils/codes.py` | Move the rate limiter into `core`; `web.app.security` re-exports it |

## Database

One PostgreSQL database, built only by the Alembic migrations in
`migrations/`. The models must describe exactly the migrated schema;
`web/tests/unit/test_schema_drift.py` fails on any difference. Tests run on
a schema built by those migrations, isolated per test run (see
`web/tests/conftest.py`).

## Refactoring plan

Each step is a separate pull request. Behaviour, URLs, response formats,
authentication and deployment stay the same until stage 3.

1. **Boundaries** (this step): this document, the boundary test, `shared/`.
2. **API registration**: API blueprints are registered by an `api` package,
   pages by `web`; the URL map stays identical.
3. **One module at a time**: move a module's API routes into `api/` and the
   database work they still do into `core` services, with tests green after
   each module.
4. **Interim audit**: what is separated, what remains in routes, test
   coverage.

Later stages (API v1 with one error format and OpenAPI, a separate API
service, caching and background jobs) start only after the interim audit.
