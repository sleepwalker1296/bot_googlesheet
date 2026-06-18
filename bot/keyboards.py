from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


MAIN_MENU_ADD = "menu:add"
MAIN_MENU_LAST = "menu:last"
MAIN_MENU_CANCEL = "menu:cancel"

OPERATION_EXPENSE = "expense"
OPERATION_INCOME = "income"
OPERATION_TRANSFER = "transfer"

CONFIRM_SAVE = "confirm:save"
CONFIRM_EDIT = "confirm:edit"
CONFIRM_CANCEL = "confirm:cancel"
COMMENT_SKIP = "comment:skip"

ACCOUNTS = (
    "РС тинькоф",
    "Т-банк Спец карта",
    "Наличка Илья",
)

EXPENSE_CATEGORIES = (
    "Закупка товара РФ",
    "Закупка товара Китай",
    "Логистика и карго",
    "Реклама",
    "Аренда",
    "Зарплаты / выплаты",
    "Налоги",
    "Комиссии",
    "Другое",
)

INCOME_CATEGORIES = (
    "Оплата от клиента",
    "Продажа товара",
    "Возврат средств",
    "Перевод",
    "Другое",
)

TRANSFER_CATEGORIES = (
    "Перевод между своими счетами",
    "Снятие наличных",
    "Внесение наличных",
    "Другое",
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить операцию", callback_data=MAIN_MENU_ADD)],
            [InlineKeyboardButton(text="📊 Последние операции", callback_data=MAIN_MENU_LAST)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=MAIN_MENU_CANCEL)],
        ]
    )


def operation_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Расход", callback_data=f"operation:{OPERATION_EXPENSE}")],
            [InlineKeyboardButton(text="💰 Доход", callback_data=f"operation:{OPERATION_INCOME}")],
            [InlineKeyboardButton(text="🔁 Перевод между счетами", callback_data=f"operation:{OPERATION_TRANSFER}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CONFIRM_CANCEL)],
        ]
    )


def accounts_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=account, callback_data=f"{prefix}:{index}")]
        for index, account in enumerate(ACCOUNTS)
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CONFIRM_CANCEL)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_keyboard(operation_type: str) -> InlineKeyboardMarkup:
    categories = EXPENSE_CATEGORIES if operation_type == OPERATION_EXPENSE else INCOME_CATEGORIES
    return _indexed_keyboard(categories, "category")


def transfer_categories_keyboard() -> InlineKeyboardMarkup:
    return _indexed_keyboard(TRANSFER_CATEGORIES, "transfer_category")


def comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Без комментария", callback_data=COMMENT_SKIP)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CONFIRM_CANCEL)],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=CONFIRM_SAVE)],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=CONFIRM_EDIT)],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=CONFIRM_CANCEL)],
        ]
    )


def _indexed_keyboard(items: tuple[str, ...], prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=item, callback_data=f"{prefix}:{index}")]
        for index, item in enumerate(items)
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CONFIRM_CANCEL)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
