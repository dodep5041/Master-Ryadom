
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import get_settings
from database import init_db
from handlers.admin import router as admin_router
from handlers.start import router as start_router
from handlers.application import router as application_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    init_db()

    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(application_router)

    async with Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    ) as bot:
        logger.info("Бот запускается...")

        try:
            await dp.start_polling(bot)
        finally:
            logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Работа приложения завершена.")
