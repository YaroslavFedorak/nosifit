# NosiFit Telegram Bot

The Telegram bot is a lightweight client for quick NosiFit data entry.

The bot is built with aiogram 3 and communicates with the NosiFit backend through its API. It does not access PostgreSQL directly.

## Authentication

Each Telegram user signs in with their own NosiFit account.

The flow is:

1. Open the bot with /start.
2. Press **🔐 Увійти**.
3. Enter the same email and password used on the NosiFit website.
4. The bot creates an authenticated NosiFit HTTP session for that Telegram user.
5. Nutrition actions use that user's NosiFit account.
6. Press **🚪 Вийти** or use /logout to remove the session.

The password is used only during login and is not stored after authentication. Active sessions are kept in memory, so users need to sign in again after a bot restart.

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

## Development

Create a .env file with:

TELEGRAM_BOT_TOKEN=your_bot_token
NOSI_FIT_BASE_URL=http://localhost:5000

Run the bot:

python -m telegram_bot.bot

FSM state currently uses aiogram MemoryStorage, so an in-progress login or meal is lost if the bot process restarts.
