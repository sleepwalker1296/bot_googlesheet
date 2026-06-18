import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.config import get_settings
from bot.keyboards import MAIN_MENU_ADD, MAIN_MENU_CANCEL, MAIN_MENU_LAST, main_menu_keyboard, operation_type_keyboard
from bot.services.google_sheets import GoogleSheetsService
from bot.services.validators import format_amount
from bot.states import OperationStates


router = Router(name="start")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "<b>Финансовый бот</b>\n\n"
        "Здесь можно быстро записать расход, доход или перевод между счетами. "
        "Данные сохраняются в Google Sheets автоматически.\n\n"
        "Выберите действие:"
    )

    settings = get_settings()
    if settings.start_image_file and settings.start_image_file.exists():
        await message.answer_photo(
            photo=FSInputFile(settings.start_image_file),
            caption=text,
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Краткая инструкция</b>\n\n"
        "/start - главное меню\n"
        "/last - последние 5 операций\n"
        "/cancel - отменить текущую операцию\n\n"
        "Обычная запись: тип операции -> счет -> сумма -> категория -> комментарий -> подтверждение.\n"
        "Перевод: счет списания -> счет пополнения -> сумма -> тип перевода -> подтверждение."
    )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Операция отменена. Можно начать новую запись:", reply_markup=main_menu_keyboard())


@router.message(Command("last"))
async def last_command(message: Message, sheets: GoogleSheetsService) -> None:
    await _send_last_operations(message, sheets)


@router.callback_query(F.data == MAIN_MENU_ADD)
async def add_operation(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(OperationStates.operation_type)
    text = (
        "<b>Новая операция</b>\n\n"
        "Что нужно записать?"
    )
    if callback.message.photo:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(text, reply_markup=operation_type_keyboard())
    else:
        await callback.message.edit_text(text, reply_markup=operation_type_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_MENU_LAST)
async def last_operations(callback: CallbackQuery, sheets: GoogleSheetsService) -> None:
    await _send_last_operations(callback.message, sheets)
    await callback.answer()


@router.callback_query(F.data == MAIN_MENU_CANCEL)
async def cancel_from_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = "Действие отменено. Используйте /start, чтобы открыть меню."
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=None)
    else:
        await callback.message.edit_text(text)
    await callback.answer()


async def _send_last_operations(message: Message, sheets: GoogleSheetsService) -> None:
    try:
        rows = sheets.get_last_operations(limit=5)
    except Exception:
        logger.exception("Failed to load last operations")
        await message.answer("Не удалось получить последние операции из Google Sheets.")
        return

    if not rows:
        await message.answer(
            "<b>Последние операции</b>\n\n"
            "Пока записей нет. Нажмите «Добавить операцию», чтобы внести первую.",
            reply_markup=main_menu_keyboard(),
        )
        return

    total_income = 0.0
    total_expense = 0.0
    lines = ["<b>Последние 5 операций</b>"]
    for index, row in enumerate(rows, start=1):
        date, time, operation_type, source, category, amount, comment = row[:7]
        amount_value = _amount_to_float(amount)
        if operation_type == "Доход":
            total_income += amount_value
        elif operation_type == "Расход":
            total_expense += amount_value

        icon = _operation_icon(operation_type)
        sign = "+" if operation_type == "Доход" else "-"
        if operation_type == "Перевод":
            sign = ""
        comment_text = f"\n   Комментарий: {escape(comment)}" if comment else ""
        lines.append(
            "\n"
            f"<b>{index}. {icon} {escape(operation_type)}</b>\n"
            f"   Сумма: <b>{sign}{format_amount(amount_value)} ₽</b>\n"
            f"   Счет: {escape(source)}\n"
            f"   Категория: {escape(category)}\n"
            f"   Дата: {escape(date)} в {escape(time)}"
            f"{comment_text}"
        )

    if total_income or total_expense:
        lines.append(
            "\n"
            "<b>Итого по списку</b>\n"
            f"   Доходы: +{format_amount(total_income)} ₽\n"
            f"   Расходы: -{format_amount(total_expense)} ₽"
        )

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


def _operation_icon(operation_type: str) -> str:
    if operation_type == "Доход":
        return "💰"
    if operation_type == "Расход":
        return "💸"
    if operation_type == "Перевод":
        return "🔁"
    return "•"


def _amount_to_float(value: str) -> float:
    normalized = str(value).replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return 0.0
