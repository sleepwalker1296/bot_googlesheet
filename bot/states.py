from aiogram.fsm.state import State, StatesGroup


class OperationStates(StatesGroup):
    operation_type = State()
    source = State()
    amount = State()
    category = State()
    comment = State()
    confirm = State()


class TransferStates(StatesGroup):
    from_account = State()
    to_account = State()
    amount = State()
    transfer_category = State()
    comment = State()
    confirm = State()
