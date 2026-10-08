# Deploying NosiFit to Railway

Two services from this one repository plus a Postgres database and a small
Redis (rate-limit counters only).

## 1. Project and database

1. Railway → **New Project** → **Deploy PostgreSQL**.
2. In the same project: **New** → **GitHub Repo** → `NosiFit`. Rename the service to `web`.
3. In the same project: **New** → **Database** → **Redis**. Keep the default name `Redis`.
   It must be in the *same project and environment* as `web`: private networking
   does not cross projects, and the public URL would cost egress and expose Redis.

## 2. `web` service

**Variables**

| Name | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference to the Postgres service) |
| `SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | from a **separate** GitHub OAuth App for production |
| `BREVO_API_KEY` | brevo.com (free: 300 emails/day) → *SMTP & API* → *API Keys* |
| `MAIL_FROM` | `NosiFit <you@gmail.com>` — a sender verified in Brevo (*Senders, Domains & Dedicated IPs* → *Senders*); no own domain needed |
| `TZ` | `Europe/Kyiv` — the server's "today" becomes the users' day |
| `PUBLIC_BASE_URL` | only with a custom domain, e.g. `https://nosifit.com` — base of password-reset and Telegram link URLs. Defaults to `https://$RAILWAY_PUBLIC_DOMAIN`; reset emails and Telegram links are refused when neither is set |
| `RATELIMIT_REDIS_URL` | `${{Redis.REDIS_URL}}` — **required**: the private (`redis.railway.internal`) URL, never `REDIS_PUBLIC_URL`. The app does not start in production without it |
| `TELEGRAM_BOT_API_SECRET` | output of `python -c "import secrets; print(secrets.token_hex(32))"`; the **same value** on the `bot` service. Signs the bot's `/api/telegram/*` requests. Unset → Telegram sign-in is off (404). Shorter than 32 characters → the app refuses to start |
| `TELEGRAM_BOT_USERNAME` | optional, bot username without `@`: the profile page then shows a "Connect Telegram" button (`t.me/<bot>?start=connect`) |

`postgres://` / `postgresql://` URLs are converted to the psycopg 3 driver automatically (`backend/config.py`).
Secure + HttpOnly cookies, https links behind the proxy (ProxyFix), HSTS and the SECRET_KEY check switch on automatically on Railway.
After the first deploy of the session-binding change every user is logged out once (old sessions carry no password fingerprint).

**Settings**

- **Start command**: leave empty — `Procfile` runs gunicorn.
- **Pre-deploy command**: `flask --app run db upgrade`
- **Healthcheck path**: `/healthz`
- **Networking** → **Generate Domain** → e.g. `nosifit-production.up.railway.app`.

## 3. Redis (rate limiting)

Redis holds only rate-limit counters: keys are HMACs of email/IP/user id, values
are integers, every key expires within an hour. No sessions, cache, codes or
personal data, so it needs neither persistence nor replicas.

- **Cost**: usage-based. Idle Redis with these keys uses a few MB of RAM and
  almost no CPU, i.e. cents per month (RAM is $10/GB/month), well inside the
  plan's included usage.
- **Smallest footprint** (optional): in the Redis service settings limit
  memory and turn persistence off by adding to the start command
  `--maxmemory 25mb --maxmemory-policy volatile-ttl --save "" --appendonly no`.
  Keep `--requirepass`. Without persistence a Redis restart clears the counters
  (windows are at most one hour), which is acceptable here.
- **Do not** enable High Availability or add a public TCP proxy.
- **When Redis is down** login, registration codes, password reset, email change,
  password change, account deletion and Telegram sign-in/linking answer `503`
  until it is back; the rest of the site keeps working. This is deliberate: no
  unlimited attempts.

## 4. OAuth callbacks

- Google Cloud Console → Credentials → OAuth client → *Authorized redirect URIs*:
  `https://<domain>/auth/google/callback`
- GitHub → Settings → Developer settings → OAuth Apps → new app for production:
  *Authorization callback URL* `https://<domain>/auth/github/callback`.
  A GitHub OAuth App has only one callback URL, so keep the old app for localhost.

## 5. Reference data (once)

After the first successful deploy, in the `web` service shell (or `railway run`):

```
python -m web.scripts.seed_all
```

Exercises, muscles, equipment, 78 products and recovery habits. Safe to run again.
The `pg_trgm` extension is created by migration `b4a7d1e8c2f0`.

## 6. `bot` service

1. **New** → **GitHub Repo** → `NosiFit` again, rename to `bot`.
2. **Start command**: `python -m telegram_bot.bot`
3. **Pre-deploy command**: empty. **Replicas**: 1 (two pollers with one token conflict).
4. Variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_API_SECRET=${{web.TELEGRAM_BOT_API_SECRET}}`
   (reference to the web service's value), `NOSI_FIT_BASE_URL=https://<web domain>`,
   `NOSI_FIT_TIMEZONE=Europe/Kyiv`. The bot does not start without the secret.
5. Stop the bot on your computer: Telegram allows only one running poller per token.
6. Deploy `web` (its pre-deploy migration creates `telegram_identities` and
   `telegram_link_tokens`) before or together with `bot`.

The bot never handles NosiFit passwords: users sign in with their Telegram
account, create an account with an emailed code, or connect an existing
account through a one-time link confirmed in the browser. Users of the old
email + password bot press **🔐 Увійти** and pick how they sign in, once (the old bot kept no
stored data, so nothing is migrated). Details: [telegram_bot/README.md](telegram_bot/README.md).

## Checks after deploy

- `https://<domain>/healthz` → `{"status": "ok"}`
- register with email code, log in, log in with Google and GitHub
- password reset email arrives
- the bot: "Створити акаунт" with a new email, then "Увійти" and save a meal
- the bot: "Увійти" → "Увійти через Google" → the link opens Google → Connect → "Увійти" in the bot
- Profile → Connected accounts shows Telegram; Disconnect asks for the password
