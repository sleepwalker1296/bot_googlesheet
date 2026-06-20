import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from bot.keyboards import (
    ACCOUNTS,
    COMMENT_SKIP,
    CONFIRM_EDIT,
    CONFIRM_SAVE,
    NAV_BACK,
    TRANSFER_CATEGORIES,
    accounts_keyboard,
    comment_keyboard,
    confirm_keyboard,
    input_step_keyboard,
    main_menu_keyboard,
    operation_type_keyboard,
    transfer_categories_keyboard,
)
from bot.services.google_sheets import GoogleSheetsService, TransferRecord, UserInfo
from bot.services.validators import format_amount, parse_amount
from bot.states import OperationStates, TransferStates


router = Router(name="transfer")
logger = logging.getLogger(__name__)


@router.callback_query(TransferStates.from_account, F.data.startswith("from_account:"))
async def choose_from_account(callback: CallbackQuery, state: FSMContext) -> None:
    account = _item_by_callback(callback.data, ACCOUNTS)
    if account is None:
        await callback.answer("Неизвестный счет", show_alert=True)
        return

    await state.update_data(from_account=account)
    await state.set_state(TransferStates.to_account)
    await callback.message.edit_text(
        f"<b>Счет списания</b>\n\n"
        f"Списываем с: {escape(account)}\n\n"
        "Теперь выберите счет пополнения:",
        reply_markup=accounts_keyboard("to_account"),
    )
    await callback.answer()


@router.callback_query(TransferStates.to_account, F.data.startswith("to_account:"))
async def choose_to_account(callback: CallbackQuery, state: FSMContext) -> None:
    account = _item_by_callback(callback.data, ACCOUNTS)
    if account is None:
        await callback.answer("Неизвестный счет", show_alert=True)
        return

    await state.update_data(to_account=account)
    await state.set_state(TransferStates.amount)
    await callback.message.edit_text(
        f"<b>Счет пополнения</b>\n\n"
        f"Зачисляем на: {escape(account)}\n\n"
        "Введите сумму перевода. Например: <code>12500</code> или <code>12 500,50</code>.",
        reply_markup=input_step_keyboard(),
    )
    await callback.answer()


@router.message(TransferStates.amount)
async def enter_transfer_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "Не получилось распознать сумму.\n\n"
            "Введите число больше 0. Подойдут форматы: <code>1250</code>, <code>1 250</code>, "
            "<code>1250.50</code>, <code>1250,50</code>.",
            reply_markup=input_step_keyboard(),
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(TransferStates.transfer_category)
    await message.answer(
        f"<b>Сумма перевода: {format_amount(amount)} ₽</b>\n\n"
        "Выберите тип перевода:",
        reply_markup=transfer_categories_keyboard(),
    )


@router.callback_query(TransferStates.transfer_category, F.data.startswith("transfer_category:"))
async def choose_transfer_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = _item_by_callback(callback.data, TRANSFER_CATEGORIES)
    if category is None:
        await callback.answer("Неизвестная операция", show_alert=True)
        return

    await state.update_data(category=category)
    await state.set_state(TransferStates.comment)
    await callback.message.edit_text(
        f"<b>Тип перевода выбран</b>\n\n"
        f"{escape(category)}\n\n"
        "Можно добавить комментарий, например куда переложили деньги или зачем. "
        "Если не нужно, нажмите «Без комментария».",
        reply_markup=comment_keyboard(),
    )
    await callback.answer()


@router.callback_query(TransferStates.from_account, F.data == NAV_BACK)
async def back_from_transfer_from_account(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OperationStates.operation_type)
    await callback.message.edit_text(
        "<b>Новая операция</b>\n\n"
        "Что нужно записать?",
        reply_markup=operation_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(TransferStates.to_account, F.data == NAV_BACK)
async def back_from_transfer_to_account(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TransferStates.from_account)
    await callback.message.edit_text(
        "<b>Перевод между счетами</b>\n\n"
        "С какого счета списать деньги?",
        reply_markup=accounts_keyboard("from_account"),
    )
    await callback.answer()


@router.callback_query(TransferStates.amount, F.data == NAV_BACK)
async def back_from_transfer_amount(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    from_account = data.get("from_account", "не выбран")
    await state.set_state(TransferStates.to_account)
    await callback.message.edit_text(
        f"<b>Счет списания</b>\n\n"
        f"Списываем с: {escape(from_account)}\n\n"
        "Теперь выберите счет пополнения:",
        reply_markup=accounts_keyboard("to_account"),
    )
    await callback.answer()


@router.callback_query(TransferStates.transfer_category, F.data == NAV_BACK)
async def back_from_transfer_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    to_account = data.get("to_account", "не выбран")
    await state.set_state(TransferStates.amount)
    await callback.message.edit_text(
        f"<b>Счет пополнения</b>\n\n"
        f"Зачисляем на: {escape(to_account)}\n\n"
        "Введите сумму перевода. Например: <code>12500</code> или <code>12 500,50</code>.",
        reply_markup=input_step_keyboard(),
    )
    await callback.answer()


@router.callback_query(TransferStates.comment, F.data == NAV_BACK)
async def back_from_transfer_comment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TransferStates.transfer_category)
    await callback.message.edit_text(
        "Выберите тип перевода:",
        reply_markup=transfer_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(TransferStates.confirm, F.data == NAV_BACK)
async def back_from_transfer_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(TransferStates.comment)
    await callback.message.edit_text(
        f"<b>Тип перевода выбран</b>\n\n"
        f"{escape(data['category'])}\n\n"
        "Можно добавить комментарий, например куда переложили деньги или зачем. "
        "Если не нужно, нажмите «Без комментария».",
        reply_markup=comment_keyboard(),
    )
    await callback.answer()


@router.message(TransferStates.comment)
async def enter_transfer_comment(message: Message, state: FSMContext) -> None:
    await state.update_data(comment=(message.text or "").strip())
    await _show_confirmation(message, state)


@router.callback_query(TransferStates.comment, F.data == COMMENT_SKIP)
async def skip_transfer_comment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(comment="")
    await _show_confirmation(callback.message, state)
    await callback.answer()


@router.callback_query(TransferStates.confirm, F.data == CONFIRM_SAVE)
async def confirm_transfer(callback: CallbackQuery, state: FSMContext, sheets: GoogleSheetsService) -> None:
    data = await state.get_data()
    record = TransferRecord(
        from_account=data["from_account"],
        to_account=data["to_account"],
        category=data["category"],
        amount=data["amount"],
        comment=data.get("comment", ""),
        user=_user_info(callback.from_user),
    )

    try:
        sheets.append_transfer(record)
    except Exception:
        logger.exception("Failed to save transfer")
        await callback.message.answer(
            "Не удалось сохранить перевод в Google Sheets. Проверьте доступ к таблице и попробуйте еще раз."
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text("✅ <b>Операция сохранена в Google Sheets</b>", reply_markup=None)
    await callback.message.answer("Можно добавить следующую запись:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(TransferStates.confirm, F.data == CONFIRM_EDIT)
async def edit_transfer(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TransferStates.from_account)
    await callback.message.edit_text(
        "<b>Изменение перевода</b>\n\n"
        "Заполним перевод заново. Выберите счет списания:",
        reply_markup=accounts_keyboard("from_account"),
    )
    await callback.answer()


async def _show_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(TransferStates.confirm)
    comment = data.get("comment") or "Без комментария"
    await message.answer(
        "<b>Проверьте перевод перед записью</b>\n\n"
        "Тип: <b>Перевод</b>\n"
        f"Счет списания: {escape(data['from_account'])}\n"
        f"Счет пополнения: {escape(data['to_account'])}\n"
        f"Операция: {escape(data['category'])}\n"
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


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
    )
