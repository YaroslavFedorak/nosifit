# Deploying NosiFit to Railway

Two services from this one repository plus a Postgres database.

## 1. Project and database

1. Railway → **New Project** → **Deploy PostgreSQL**.
2. In the same project: **New** → **GitHub Repo** → `NosiFit`. Rename the service to `web`.

## 2. `web` service

**Variables**

| Name | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference to the Postgres service) |
| `SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | from a **separate** GitHub OAuth App for production |
| `SENDGRID_API_KEY` | from SendGrid → Settings → API Keys (permission *Mail Send*) |
| `MAIL_FROM` | `NosiFit <you@example.com>` — must be a sender verified in SendGrid (Settings → Sender Authentication) |
| `TZ` | `Europe/Kyiv` — the server's "today" becomes the users' day |

`postgres://` / `postgresql://` URLs are converted to the psycopg 3 driver automatically (`backend/config.py`).
Secure + HttpOnly cookies, https links behind the proxy (ProxyFix) and the SECRET_KEY check switch on automatically on Railway.

**Settings**

- **Start command**: leave empty — `Procfile` runs gunicorn.
- **Pre-deploy command**: `flask --app run db upgrade`
- **Healthcheck path**: `/healthz`
- **Networking** → **Generate Domain** → e.g. `nosifit-production.up.railway.app`.

## 3. OAuth callbacks

- Google Cloud Console → Credentials → OAuth client → *Authorized redirect URIs*:
  `https://<domain>/auth/google/callback`
- GitHub → Settings → Developer settings → OAuth Apps → new app for production:
  *Authorization callback URL* `https://<domain>/auth/github/callback`.
  A GitHub OAuth App has only one callback URL, so keep the old app for localhost.

## 4. Reference data (once)

After the first successful deploy, in the `web` service shell (or `railway run`):

```
python -m web.scripts.seed_all
```

Exercises, muscles, equipment, 78 products and recovery habits. Safe to run again.
The `pg_trgm` extension is created by migration `b4a7d1e8c2f0`.

## 5. `bot` service

1. **New** → **GitHub Repo** → `NosiFit` again, rename to `bot`.
2. **Start command**: `python -m telegram_bot.bot`
3. **Pre-deploy command**: empty. **Replicas**: 1 (two pollers with one token conflict).
4. Variables: `TELEGRAM_BOT_TOKEN`, `NOSI_FIT_BASE_URL=https://<web domain>`, `NOSI_FIT_TIMEZONE=Europe/Kyiv`.
5. Stop the bot on your computer: Telegram allows only one running poller per token.

## Checks after deploy

- `https://<domain>/healthz` → `{"status": "ok"}`
- register with email code, log in, log in with Google and GitHub
- password reset email arrives
- the bot logs in and saves a meal
