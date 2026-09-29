import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from telegram_bot.config import TelegramConfig
from telegram_bot.handlers.common import cancel, unknown
from telegram_bot.handlers.nutrition import nutrition
from telegram_bot.handlers.start import help_command, start
from telegram_bot.handlers.water import water
from telegram_bot.handlers.weight import weight
from telegram_bot.keyboards.main import NUTRITION, WATER, WEIGHT


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_application(config: TelegramConfig) -> Application:
    application = Application.builder().token(config.bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))

    application.add_handler(
        MessageHandler(filters.Regex(f"^{NUTRITION}$"), nutrition)
    )
    application.add_handler(
        MessageHandler(filters.Regex(f"^{WATER}$"), water)
    )
    application.add_handler(
        MessageHandler(filters.Regex(f"^{WEIGHT}$"), weight)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unknown)
    )

    return application


def main() -> None:
    config = TelegramConfig.from_env()
    application = create_application(config)

    logger.info("Starting NosiFit Telegram bot")
    logger.info("NosiFit API: %s", config.nosi_fit_base_url)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
