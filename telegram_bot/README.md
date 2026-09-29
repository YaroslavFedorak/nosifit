# NosiFit Telegram Bot

The Telegram bot is a lightweight client for quick NosiFit data entry.

## Development

Create a \`.env\` file in the repository root:

\`\`\`
TELEGRAM_BOT_TOKEN=your_bot_token
NOSI_FIT_BASE_URL=http://localhost:5000
\`\`\`

Start the bot with:

\`\`\`powershell
python -m telegram_bot.bot
\`\`\`

The current MVP provides \`/start\`, \`/help\`, \`/cancel\`, and the main menu for nutrition, water, and weight.
