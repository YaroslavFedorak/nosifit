# NosiFit Telegram Bot

The Telegram bot is a lightweight client for quick NosiFit data entry.

The bot is built with aiogram 3 and communicates with the NosiFit backend through its API. It does not access PostgreSQL directly.

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
NOSI_FIT_EMAIL=your_nosifit_email
NOSI_FIT_PASSWORD=your_nosifit_password

The Telegram bot authenticates against the normal NosiFit login endpoint and keeps the resulting session in memory. Do not commit credentials.

Run the bot:

python -m telegram_bot.bot

The current nutrition integration uses one configured NosiFit account. A multi-account Telegram to NosiFit linking flow should be added before exposing the bot to multiple independent users.

FSM state currently uses aiogram MemoryStorage, so an in-progress meal is lost if the bot process restarts.
