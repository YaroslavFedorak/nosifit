# NosiFit Telegram Bot

The Telegram bot is a lightweight client for quick NosiFit data entry.

The bot is built with **aiogram 3** and communicates with the NosiFit backend through its API. It does not access PostgreSQL directly.

## Development

Create a `.env` file in the repository root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
NOSI_FIT_BASE_URL=http://localhost:5000
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the bot:

```powershell
python -m telegram_bot.bot
```

The current MVP provides `/start`, `/help`, `/cancel`, and the main menu for nutrition, water, and weight.