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
| `api` | HTTP endpoints: validate the request, call `core`, shape the response | `api/` registers every blueprint under `/api/`; route modules move from `web/app/routes/` into `api/routes/` one at a time (done: injuries, equipment, onboarding, translations, dashboard, recovery) |
| `web` | Pages, templates, static files, sign-in and OAuth flows | `web/app/` |
| `bot` | Telegram interface; talks to the backend only through the HTTP API | `telegram_bot/` |
| `shared` | Pure helpers several components need: bot request signing, barcode normalisation, the translation files and their loader | `shared/` |
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
  belongs in `core`. Modules in `api/routes/` do not import `web` at all.

`web/tests/unit/test_architecture.py` checks these rules on every test run,
and also that every route under `/api/` is registered by `api.register_api`
while pages and form posts are registered by `web`.
There are no known violations; the test lists any it has to tolerate.

## Database

One PostgreSQL database, built only by the Alembic migrations in
`migrations/`. The models must describe exactly the migrated schema;
`web/tests/unit/test_schema_drift.py` fails on any difference. Tests run on
a schema built by those migrations, isolated per test run (see
`web/tests/conftest.py`).

## Refactoring plan

Each step is a separate pull request. Behaviour, URLs, response formats,
authentication and deployment stay the same until the interim audit.

1. **Boundaries**: this document, the boundary test, `shared/`. Done.
2. **API registration**: `api.register_api` registers the ten API
   blueprints, `web.app.routes.register_pages` the pages; the URL map is
   identical. Done.
   JSON endpoints outside `/api/` (`/profile/*` posts, `/plan/json`,
   `/questionnaire/` post, `/verify/send_code`, Telegram link confirm) stay
   in `web` for now: they serve the site's own forms, and whether each one
   becomes part of the public API is decided in API v1.
3. **One module at a time**: move a module's API routes into `api/routes/`
   and the database work they still do into `core` services, with tests
   green after each module. Done: injuries, equipment, onboarding,
   translations, dashboard, recovery. The test lists the API blueprints
   still in `web`.
4. **Interim audit**: what is separated, what remains in routes, test
   coverage.

Later stages (API v1 with one error format and OpenAPI, a separate API
service, caching and background jobs) start only after the interim audit.
