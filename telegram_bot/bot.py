import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from telegram_bot.config import TelegramConfig
from telegram_bot.handlers import auth, common, nutrition, start, water, weight
from telegram_bot.security import is_private_human

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    # Groups, channels and bots are ignored entirely (see telegram_bot.security).
    dispatcher.message.filter(is_private_human)
    dispatcher.callback_query.filter(is_private_human)
    dispatcher.edited_message.filter(is_private_human)
    dispatcher.include_router(auth.router)
    dispatcher.include_router(start.router)
    dispatcher.include_router(nutrition.router)
    dispatcher.include_router(water.router)
    dispatcher.include_router(weight.router)
    dispatcher.include_router(common.router)
    return dispatcher


async def main() -> None:
    # Fails fast without TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_API_SECRET.
    config = TelegramConfig.from_env()
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = create_dispatcher()
    logger.info("Starting NosiFit Telegram bot")
    logger.info("NosiFit API: %s", config.nosi_fit_base_url)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
