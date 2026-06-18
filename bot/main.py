import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from gspread.exceptions import APIError, WorksheetNotFound

from bot.config import get_settings
from bot.handlers.operation import router as operation_router
from bot.handlers.start import router as start_router
from bot.handlers.transfer import router as transfer_router
from bot.services.google_sheets import GoogleSheetsService
from bot.utils.logger import setup_logging


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    settings = get_settings()
    try:
        sheets = GoogleSheetsService(
            sheet_id=settings.google_sheet_id,
            service_account_json=settings.google_service_account_json,
            timezone=settings.timezone,
        )
        sheets.ensure_structure()
    except PermissionError as error:
        cause = getattr(error, "__cause__", None)
        if cause:
            logger.error("Google Sheets отказал в доступе: %s", cause)
        logger.error(
            "Нет доступа к Google Sheets. Проверьте, что Google Sheets API включен "
            "в проекте сервисного аккаунта и что client_email из JSON добавлен "
            "редактором в Google Таблицу."
        )
        logger.error("Google Sheet ID из .env: %s", settings.google_sheet_id)
        logger.error("JSON сервисного аккаунта: %s", settings.google_service_account_json)
        raise SystemExit(1)
    except APIError as error:
        logger.error("Ошибка Google Sheets API при запуске: %s", error)
        raise SystemExit(1)
    except WorksheetNotFound as error:
        logger.error("Не найден один из обязательных листов клиента: %s", error)
        logger.error("В таблице должны быть листы: РС тинькоф, Т-банк Спец карта, Наличка Илья")
        raise SystemExit(1)
    except FileNotFoundError as error:
        logger.error("%s", error)
        raise SystemExit(1)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage(), sheets=sheets)
    dispatcher.include_router(start_router)
    dispatcher.include_router(operation_router)
    dispatcher.include_router(transfer_router)

    await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
