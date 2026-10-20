import asyncio
import logging

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from telegram_bot.config import TelegramConfig
from telegram_bot.handlers import (
    auth,
    common,
    consent,
    language,
    nutrition,
    start,
    training,
    water,
    weight,
)
from telegram_bot.i18n import LanguageMiddleware
from telegram_bot.security import is_private_human

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram/webhook"


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    # Groups, channels and bots are ignored entirely (see telegram_bot.security).
    dispatcher.message.filter(is_private_human)
    dispatcher.callback_query.filter(is_private_human)
    dispatcher.edited_message.filter(is_private_human)
    # The language of the update, set before any filter or handler runs.
    for observer in (dispatcher.message, dispatcher.callback_query, dispatcher.edited_message):
        observer.outer_middleware(LanguageMiddleware())
    dispatcher.include_router(auth.router)
    dispatcher.include_router(consent.router)
    dispatcher.include_router(start.router)
    # Before training/nutrition: their search states take any text.
    dispatcher.include_router(language.router)
    # Before nutrition: its search states take any text, the training
    # button included; training text handlers skip menu buttons.
    dispatcher.include_router(training.router)
    dispatcher.include_router(nutrition.router)
    dispatcher.include_router(water.router)
    dispatcher.include_router(weight.router)
    dispatcher.include_router(common.router)
    return dispatcher


def create_webhook_app(bot: Bot, dispatcher: Dispatcher, config: TelegramConfig) -> web.Application:
    """aiohttp app that takes updates on WEBHOOK_PATH.

    Telegram sends config.webhook_secret in X-Telegram-Bot-Api-Secret-Token;
    SimpleRequestHandler answers 401 to any request without it.
    """
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher, bot=bot, secret_token=config.webhook_secret
    ).register(app, path=WEBHOOK_PATH)
    app.router.add_get("/health", lambda _request: web.Response(text="ok"))
    setup_application(app, dispatcher, bot=bot)
    return app


async def run_webhook(bot: Bot, dispatcher: Dispatcher, config: TelegramConfig) -> None:
    await bot.set_webhook(
        f"{config.webhook_url}{WEBHOOK_PATH}",
        secret_token=config.webhook_secret,
        allowed_updates=dispatcher.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    runner = web.AppRunner(create_webhook_app(bot, dispatcher, config))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.port).start()
    logger.info("Webhook mode: %s%s, port %s", config.webhook_url, WEBHOOK_PATH, config.port)
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    # Fails fast without TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_API_SECRET.
    config = TelegramConfig.from_env()
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = create_dispatcher()
    logger.info("Starting NosiFit Telegram bot")
    logger.info("NosiFit API: %s", config.nosi_fit_base_url)
    try:
        if config.webhook_url:
            await run_webhook(bot, dispatcher, config)
        else:
            await bot.delete_webhook(drop_pending_updates=True)
            await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
