from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials


ACCOUNT_SHEETS = ("РС тинькоф", "Т-банк Спец карта", "Наличка Илья")
SHEET_ALIASES = {
    "РС тинькоф": ("РС тинькоф", "РС Тинькоф", "РС Тинькофф"),
    "Т-банк Спец карта": ("Т-банк Спец карта", "Т-Банк спец карта", "Т-Банк спец карат", "т-банк спец карта"),
    "Наличка Илья": ("Наличка Илья", "наличка илья"),
}
ACCOUNT_LEDGER_HEADERS = ["Дата", "Поступило", "Списано", "Назначение"]
SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


@dataclass(frozen=True)
class UserInfo:
    telegram_id: int
    username: str
    full_name: str


@dataclass(frozen=True)
class OperationRecord:
    operation_type: str
    source: str
    category: str
    amount: float
    comment: str
    user: UserInfo


@dataclass(frozen=True)
class TransferRecord:
    from_account: str
    to_account: str
    category: str
    amount: float
    comment: str
    user: UserInfo


class GoogleSheetsService:
    def __init__(self, sheet_id: str, service_account_json: Path, timezone: str) -> None:
        if not service_account_json.exists():
            raise FileNotFoundError(f"Файл сервисного аккаунта не найден: {service_account_json}")

        credentials = Credentials.from_service_account_file(
            str(service_account_json),
            scopes=SCOPES,
        )
        self._spreadsheet = gspread.authorize(credentials).open_by_key(sheet_id)
        self._timezone = ZoneInfo(timezone)

    def ensure_structure(self) -> None:
        for account in ACCOUNT_SHEETS:
            self._existing_worksheet(account)

    def append_operation(self, record: OperationRecord) -> None:
        account = self._canonical_account(record.source)
        if account is None:
            raise ValueError(f"Неизвестный счет: {record.source}")

        self._append_account_ledger_row(record, account)

    def append_transfer(self, record: TransferRecord) -> None:
        debit = OperationRecord(
            operation_type="Расход",
            source=record.from_account,
            category=record.category,
            amount=record.amount,
            comment=f"Перевод на {record.to_account}. {record.comment}".strip(),
            user=record.user,
        )
        credit = OperationRecord(
            operation_type="Доход",
            source=record.to_account,
            category="Перевод",
            amount=record.amount,
            comment=f"Перевод из {record.from_account}. {record.comment}".strip(),
            user=record.user,
        )
        self.append_operation(debit)
        self.append_operation(credit)

    def get_last_operations(self, limit: int = 5) -> list[list[str]]:
        operations = []
        for account in ACCOUNT_SHEETS:
            worksheet = self._existing_worksheet(account)
            rows = worksheet.get_all_values()
            for row in rows:
                normalized = row + [""] * (len(ACCOUNT_LEDGER_HEADERS) - len(row))
                date, incoming, outgoing, purpose = normalized[:4]
                if not date or date.strip().lower() == "дата":
                    continue

                amount = incoming or outgoing
                if not amount:
                    continue

                operation_type = "Доход" if incoming else "Расход"
                operations.append([date, "", operation_type, account, purpose, amount, ""])

        return operations[-limit:][::-1]

    def _append_account_ledger_row(self, record: OperationRecord, account: str) -> None:
        worksheet = self._existing_worksheet(account)
        incoming = record.amount if record.operation_type == "Доход" else ""
        outgoing = record.amount if record.operation_type == "Расход" else ""
        row = [
            self._now().strftime("%d.%m.%Y"),
            incoming,
            outgoing,
            self._ledger_purpose(record),
        ]
        next_row = self._next_ledger_row(worksheet)
        worksheet.update(
            [row],
            f"A{next_row}:D{next_row}",
            value_input_option="USER_ENTERED",
        )

    @staticmethod
    def _ledger_purpose(record: OperationRecord) -> str:
        if record.comment:
            return f"{record.category}. {record.comment}"
        return record.category

    def _now(self) -> datetime:
        return datetime.now(self._timezone)

    def _canonical_account(self, title: str) -> str | None:
        normalized_title = title.casefold()
        for account, aliases in SHEET_ALIASES.items():
            if normalized_title in {alias.casefold() for alias in aliases}:
                return account
        return None

    @staticmethod
    def _next_ledger_row(worksheet: gspread.Worksheet) -> int:
        rows = worksheet.get("A:D")
        last_filled_row = 0
        for index, row in enumerate(rows, start=1):
            if any(str(cell).strip() for cell in row[:4]):
                last_filled_row = index

        next_row = max(last_filled_row + 1, 2)
        if next_row > worksheet.row_count:
            worksheet.add_rows(next_row - worksheet.row_count)
        return next_row

    def _existing_worksheet(self, title: str) -> gspread.Worksheet:
        aliases = SHEET_ALIASES.get(title, (title,))
        for alias in aliases:
            try:
                return self._spreadsheet.worksheet(alias)
            except gspread.WorksheetNotFound:
                continue

        wanted = {alias.casefold() for alias in aliases}
        for worksheet in self._spreadsheet.worksheets():
            if worksheet.title.casefold() in wanted:
                return worksheet

        return self._spreadsheet.worksheet(title)
