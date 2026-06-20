import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, User

from bot.config import get_settings
from bot.keyboards import (
    ACCOUNTS,
    COMMENT_SKIP,
    CONFIRM_CANCEL,
    CONFIRM_EDIT,
    CONFIRM_SAVE,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    NAV_BACK,
    OPERATION_EXPENSE,
    OPERATION_INCOME,
    OPERATION_TRANSFER,
    accounts_keyboard,
    categories_keyboard,
    comment_keyboard,
    confirm_keyboard,
    input_step_keyboard,
    main_menu_keyboard,
    operation_type_keyboard,
)
from bot.services.google_sheets import GoogleSheetsService, OperationRecord, UserInfo
from bot.services.validators import format_amount, parse_amount
from bot.states import OperationStates, TransferStates


router = Router(name="operation")
logger = logging.getLogger(__name__)


@router.callback_query(OperationStates.operation_type, F.data.in_({"operation:expense", "operation:income"}))
async def choose_operation_type(callback: CallbackQuery, state: FSMContext) -> None:
    operation_type = callback.data.split(":", 1)[1]
    await state.update_data(operation_type=operation_type)
    await state.set_state(OperationStates.source)
    text = "Выберите счет, по которому проходит операция:"
    image_file = _operation_image_file(operation_type)
    if image_file and image_file.exists():
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer_photo(
            photo=FSInputFile(image_file),
            caption=text,
            reply_markup=accounts_keyboard("source"),
        )
    else:
        await callback.message.edit_text(text, reply_markup=accounts_keyboard("source"))
    await callback.answer()


@router.callback_query(OperationStates.operation_type, F.data == f"operation:{OPERATION_TRANSFER}")
async def choose_transfer_type(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TransferStates.from_account)
    await callback.message.edit_text(
        "<b>Перевод между счетами</b>\n\n"
        "С какого счета списать деньги?",
        reply_markup=accounts_keyboard("from_account"),
    )
    await callback.answer()


@router.callback_query(OperationStates.source, F.data.startswith("source:"))
async def choose_source(callback: CallbackQuery, state: FSMContext) -> None:
    source = _item_by_callback(callback.data, ACCOUNTS)
    if source is None:
        await callback.answer("Неизвестный счет", show_alert=True)
        return

    await state.update_data(source=source)
    await state.set_state(OperationStates.amount)
    text = (
        f"<b>Счет выбран</b>\n\n"
        f"Источник: {escape(source)}\n\n"
        "Введите сумму сообщением. Например: <code>12500</code> или <code>12 500,50</code>."
    )
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=input_step_keyboard())
    else:
        await callback.message.edit_text(text, reply_markup=input_step_keyboard())
    await callback.answer()


@router.message(OperationStates.amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "Не получилось распознать сумму.\n\n"
            "Введите число больше 0. Подойдут форматы: <code>1250</code>, <code>1 250</code>, "
            "<code>1250.50</code>, <code>1250,50</code>.",
            reply_markup=input_step_keyboard(),
        )
        return

    data = await state.get_data()
    operation_type = data["operation_type"]
    await state.update_data(amount=amount)
    await state.set_state(OperationStates.category)
    await message.answer(
        f"<b>Сумма: {format_amount(amount)} ₽</b>\n\n"
        "Теперь выберите категорию:",
        reply_markup=categories_keyboard(operation_type),
    )


@router.callback_query(OperationStates.category, F.data.startswith("category:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    categories = EXPENSE_CATEGORIES if data["operation_type"] == OPERATION_EXPENSE else INCOME_CATEGORIES
    category = _item_by_callback(callback.data, categories)
    if category is None:
        await callback.answer("Неизвестная категория", show_alert=True)
        return

    await state.update_data(category=category)
    await state.set_state(OperationStates.comment)
    await callback.message.edit_text(
        f"<b>Категория выбрана</b>\n\n"
        f"{escape(category)}\n\n"
        "Можно добавить короткий комментарий: поставщик, номер заказа, причина платежа. "
        "Если не нужно, нажмите «Без комментария».",
        reply_markup=comment_keyboard(),
    )
    await callback.answer()


@router.callback_query(OperationStates.source, F.data == NAV_BACK)
async def back_from_operation_source(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OperationStates.operation_type)
    await _edit_message(
        callback,
        "<b>Новая операция</b>\n\n"
        "Что нужно записать?",
        operation_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(OperationStates.amount, F.data == NAV_BACK)
async def back_from_operation_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OperationStates.source)
    await _edit_message(
        callback,
        "Выберите счет, по которому проходит операция:",
        accounts_keyboard("source"),
    )
    await callback.answer()


@router.callback_query(OperationStates.category, F.data == NAV_BACK)
async def back_from_operation_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(OperationStates.amount)
    source = data.get("source", "не выбран")
    await callback.message.edit_text(
        "<b>Счет выбран</b>\n\n"
        f"Источник: {escape(source)}\n\n"
        "Введите сумму сообщением. Например: <code>12500</code> или <code>12 500,50</code>.",
        reply_markup=input_step_keyboard(),
    )
    await callback.answer()


@router.callback_query(OperationStates.comment, F.data == NAV_BACK)
async def back_from_operation_comment(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    operation_type = data["operation_type"]
    await state.set_state(OperationStates.category)
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=categories_keyboard(operation_type),
    )
    await callback.answer()


@router.callback_query(OperationStates.confirm, F.data == NAV_BACK)
async def back_from_operation_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(OperationStates.comment)
    await callback.message.edit_text(
        f"<b>Категория выбрана</b>\n\n"
        f"{escape(data['category'])}\n\n"
        "Можно добавить короткий комментарий: поставщик, номер заказа, причина платежа. "
        "Если не нужно, нажмите «Без комментария».",
        reply_markup=comment_keyboard(),
    )
    await callback.answer()


@router.message(OperationStates.comment)
async def enter_comment(message: Message, state: FSMContext) -> None:
    comment = (message.text or "").strip()
    await state.update_data(comment=comment)
    await _show_confirmation(message, state)


@router.callback_query(OperationStates.comment, F.data == COMMENT_SKIP)
async def skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(comment="")
    await _show_confirmation(callback.message, state)
    await callback.answer()


@router.callback_query(OperationStates.confirm, F.data == CONFIRM_SAVE)
async def confirm_operation(callback: CallbackQuery, state: FSMContext, sheets: GoogleSheetsService) -> None:
    data = await state.get_data()
    record = OperationRecord(
        operation_type=_operation_title(data["operation_type"]),
        source=data["source"],
        category=data["category"],
        amount=data["amount"],
        comment=data.get("comment", ""),
        user=_user_info(callback.from_user),
    )

    try:
        sheets.append_operation(record)
    except Exception:
        logger.exception("Failed to save operation")
        await callback.message.answer(
            "Не удалось сохранить операцию в Google Sheets. Проверьте доступ к таблице и попробуйте еще раз."
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text("✅ <b>Операция сохранена в Google Sheets</b>", reply_markup=None)
    await callback.message.answer("Можно добавить следующую запись:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(OperationStates.confirm, F.data == CONFIRM_EDIT)
async def edit_operation(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OperationStates.operation_type)
    await callback.message.edit_text(
        "<b>Изменение записи</b>\n\n"
        "Заполним операцию заново. Выберите тип:",
        reply_markup=operation_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CONFIRM_CANCEL)
async def cancel_by_button(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message.photo:
        await callback.message.edit_caption(caption="Операция отменена.", reply_markup=None)
    else:
        await callback.message.edit_text("Операция отменена.")
    await callback.message.answer("Можно начать заново:", reply_markup=main_menu_keyboard())
    await callback.answer()


async def _show_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(OperationStates.confirm)
    comment = data.get("comment") or "Без комментария"
    await message.answer(
        "<b>Проверьте операцию перед записью</b>\n\n"
        f"Тип: <b>{_operation_title(data['operation_type'])}</b>\n"
        f"Источник: {escape(data['source'])}\n"
        f"Категория: {escape(data['category'])}\n"
        f"Сумма: <b>{format_amount(data['amount'])} ₽</b>\n"
        f"Комментарий: {escape(comment)}\n"
        "Дата/время: автоматически",
        reply_markup=confirm_keyboard(),
    )


def _item_by_callback(callback_data: str | None, items: tuple[str, ...]) -> str | None:
    if callback_data is None or ":" not in callback_data:
        return None
    raw_index = callback_data.split(":", 1)[1]
    try:
        index = int(raw_index)
    except ValueError:
        return None
    if index < 0 or index >= len(items):
        return None
    return items[index]


def _operation_title(operation_type: str) -> str:
    return "Расход" if operation_type == OPERATION_EXPENSE else "Доход"


def _operation_image_file(operation_type: str):
    settings = get_settings()
    if operation_type == OPERATION_INCOME:
        return settings.income_image_file
    if operation_type == OPERATION_EXPENSE:
        return settings.expense_image_file
    return None


async def _edit_message(callback: CallbackQuery, text: str, reply_markup) -> None:
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await callback.message.edit_text(text, reply_markup=reply_markup)


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
    )
