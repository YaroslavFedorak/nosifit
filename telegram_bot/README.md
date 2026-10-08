# NosiFit Telegram Bot

The Telegram bot is a lightweight client for quick NosiFit data entry.

The bot is built with aiogram 3 and communicates with the NosiFit backend through its API. It does not access PostgreSQL directly.

## Authentication

Telegram is a sign-in method of a NosiFit account, next to the password,
Google and GitHub. **The bot never asks for a NosiFit password.**

```
User
 ├── password      (optional)
 ├── Google        (oauth_accounts)
 ├── GitHub        (oauth_accounts)
 └── Telegram      (telegram_identities)
```

The identity is Telegram's numeric user id (`from_user.id`). The `@username`
is stored only for display: usernames change and can be taken over.
One Telegram account belongs to at most one NosiFit account and vice versa.

`/start` shows **🔐 Увійти**, **✨ Створити новий акаунт** and **❓ Допомога**.
The first **🔐 Увійти** of a Telegram account that is not connected yet asks
how the user signs in to the website: **Google**, **GitHub**, **email і пароль**
(or create a new account), and continues with "Connect an existing account"
below.

### Log in

The bot asks the web app to sign in the Telegram user id from the update.
If a Telegram identity exists, the web app opens an ordinary NosiFit session
(the same Flask-Login session cookie a browser gets); otherwise the bot
offers to create or connect an account.

### Create an account

1. The user enters an email.
2. The web app sends a 6-digit code (the same verification codes, expiry and
   attempt counter as the website registration). If the address already has
   an account, no code is sent: that address gets an email explaining how to
   connect Telegram instead. The bot shows the same text in both cases, so it
   cannot be used to find out which emails are registered.
3. The user enters the code; the bot deletes that message from the chat.
4. The web app creates the account (without a password) and the Telegram
   identity, and signs the bot in.

A password for the website can be set later with "Forgot password?" on the
login page (the email is already verified). Google/GitHub sign-in with the
same verified email also works.

### Connect an existing account

1. **🔐 Увійти** → the user picks Google, GitHub or email + password (also
   `/connect`, and "Connect Telegram" on the profile page, which opens
   `t.me/<bot>?start=connect`).
2. The bot sends a one-time link, valid 10 minutes, as a protected message
   (cannot be forwarded or saved). The link carries the chosen method
   (`?via=google|github|password`, a closed list): a browser without a recent
   sign-in goes straight to Google's / GitHub's sign-in page.
3. The user opens it in a browser. The first open swaps the token for a
   secret kept in that browser's session, so the URL is dead afterwards
   (copies from history or logs are useless).
4. Not signed in -> normal NosiFit login (password, Google, GitHub). A
   sign-in from the last 15 minutes is required, so a stolen or long-lived
   session cannot attach a Telegram account.
5. The page shows which Telegram account and which NosiFit account will be
   connected. Only the **Connect** button links them; the account email gets
   a notification.

An existing account is never connected because an email matches.

### Disconnect

Website → Profile → Connected accounts → Disconnect. It requires the current
password (or, without a password, a code sent to the account email), and is
refused when Telegram is the account's only way to sign in. Disconnecting
immediately ends every bot session of that Telegram account.

## Security model

- **Bot ↔ web trust.** Requests to `/api/telegram/*` are signed with
  `TELEGRAM_BOT_API_SECRET` (HMAC-SHA256 over timestamp, nonce, method, path
  and body; see `backend/app/utils/bot_signature.py`). Stale timestamps and
  reused nonces are rejected. Without the secret nobody can claim a Telegram
  id. Treat it like `SECRET_KEY`.
- **Bot sessions** are normal NosiFit sessions with no "remember me" cookie,
  revoked when the Telegram identity is disconnected, the password changes or
  the account is deleted. They can only use the nutrition API and the workout
  logging part of the training API (`/api/training/sessions/*`, exercise
  search and recent exercises); plans, tests, analytics, changing email or
  password, deleting the account and (dis)connecting sign-in methods need a
  browser session.
- **Private chats only.** Group, supergroup and channel updates and messages
  from other bots are dropped; the bot leaves groups it is added to.
- **No secrets in chat or logs.** Verification codes are deleted from the
  chat and never logged; link tokens are stored only as SHA-256 hashes; error
  messages are generic.
- **Rate limits.** The web app limits per Telegram id, per email and per
  token in Redis (fail closed: 503 when Redis is down). The bot also throttles
  per Telegram user in memory.

## Nutrition

Nutrition entry follows the same Product -> Entry -> Meal -> Day model as the web application.

The flow is:

1. Open the nutrition section.
2. Choose Add Food.
3. Select breakfast, lunch, dinner or snack.
4. Search the existing NosiFit product catalog.
5. Select a product and enter its amount.
6. Add more products if needed.
7. Save the whole meal in one action.

System and user-owned products are returned by the existing nutrition API, including localized product names.

Meals are stored with language-independent category keys (`breakfast`, `lunch`, `dinner`, `snack`). The bot shows Ukrainian names and reuses an existing meal of the same type for today instead of creating a duplicate.

Amounts are validated before they are sent (up to 5000 g / ml or 100 pcs per entry). Backend errors carry a `code` and are shown in Ukrainian.

## Training

**🏋️ Тренування** logs today's workout in the stored model: per exercise
sets x reps (or seconds) x kg and RIR. There are no separate per-set rows, so
"60x10, 60x9" is kept as one exercise with its current values, like on the
website.

1. The training screen is today's workout (or "Сьогодні ще немає вправ") with
   recent exercises as one-tap buttons.
2. Typing a name searches the exercise catalog by Ukrainian or English name
   or slug, with typos (`GET /api/training/exercises/search`); exercises done
   before rank first.
3. An exercise card shows last time's values and prefills them. "➕ Підхід"
   logs one more set with the values on the button; ±1 rep, ±2.5 kg (±5 s)
   and RIR buttons change them. Typing `60 10` or `60 10 2` (kg, reps, RIR)
   logs a set; bodyweight exercises take `12` / `12 2`, extra weight `10x12`.
4. Typing the next name opens the next exercise; "← Тренування" returns.
5. "✅ Завершити" asks once and shows the totals the server has.

Every change is saved at once: the bot sends the whole list to
`POST /api/training/sessions/complete` with today's `session_id` (from
`GET /api/training/sessions/today`) and `strict: true`, so the server
replaces that session's exercises and never creates a duplicate. A stale id
(e.g. after midnight) is rejected instead of copied into a new session.
Removing the last exercise deletes the session. Values the bot did not
change (reps "8-12", RPE 7.5 from the website) are sent back unchanged.

Taps are serialised per user, and "one more set" / delete buttons carry the
revision of the screen, so a double tap or a button on an old message does
not repeat the action. `/cancel` leaves the flow; what is logged stays.

Known limitation (follow-up): the website's workout page keeps its own list
in the browser and does not load the server's session. If the page saved
first that day, re-saving it replaces the session the bot also edits, and
exercises logged from Telegram are lost. If the bot started the day, a save
on the page creates a second session and the bot then shows the newer one.

## Water and weight

- **💧 Вода** shows today's total (manual water plus drinks logged in meals), quick buttons (+0.25 / +0.33 / +0.5 / +1 L), a custom amount (`0,4`, `300 мл`) and a way to subtract a mistaken entry (`-0,25`).
- **⚖️ Вага** shows the current weight and BMI and accepts a new value (20–400 kg).

## Setup

1. Create the bot with @BotFather and copy its token.
2. Generate one secret for both services:
   `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Bot service `.env` / variables:

   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_BOT_API_SECRET=<the secret>
   NOSI_FIT_BASE_URL=http://localhost:5000
   NOSI_FIT_TIMEZONE=Europe/Kyiv   # used for "current time" when logging a meal
   ```

4. Web service: the same `TELEGRAM_BOT_API_SECRET`, plus optionally
   `TELEGRAM_BOT_USERNAME` (without `@`) for the "Connect Telegram" button and
   `PUBLIC_BASE_URL` (required in production: link URLs are never built from
   the request's Host header).
5. Run `flask --app run db upgrade` (creates `telegram_identities` and
   `telegram_link_tokens`).

Run the bot:

```
python -m telegram_bot.bot
```

The bot refuses to start without `TELEGRAM_BOT_API_SECRET` (at least 32
characters); the web app keeps Telegram sign-in switched off (404) while the
variable is unset.

## Upgrading from the email + password bot

The previous bot logged in by sending the user's email and password to
`/auth/login` and kept the session only in memory, so there is no stored
Telegram data to migrate. After the upgrade every existing bot user presses
**🔐 Увійти**, picks how they sign in to the website and confirms in the
browser once; from then on **🔐 Увійти** is a single tap.

## Notes

FSM state and NosiFit sessions use process memory (aiogram MemoryStorage), so
an in-progress registration or meal is lost when the bot restarts, and users
press **🔐 Увійти** again. Run exactly one bot replica (one poller per token).
