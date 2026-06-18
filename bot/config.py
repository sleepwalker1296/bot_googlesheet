import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    bot_token: str
    google_sheet_id: str
    google_service_account_json: Path
    timezone: str
    start_image_file: Path | None
    income_image_file: Path | None
    expense_image_file: Path | None


@lru_cache
def get_settings() -> Settings:
    service_account_json = Path(
        _required_env("GOOGLE_SERVICE_ACCOUNT_JSON", fallback_name="GOOGLE_CREDENTIALS_FILE")
    )
    if not service_account_json.is_absolute():
        service_account_json = _resolve_existing_path(service_account_json)

    return Settings(
        bot_token=_required_env("BOT_TOKEN"),
        google_sheet_id=_required_env("GOOGLE_SHEET_ID", fallback_name="GOOGLE_SPREADSHEET_ID"),
        google_service_account_json=service_account_json,
        timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
        start_image_file=_optional_path("START_IMAGE_FILE", default="assets/start.png"),
        income_image_file=_optional_path("INCOME_IMAGE_FILE", default="assets/img1.png"),
        expense_image_file=_optional_path("EXPENSE_IMAGE_FILE", default="assets/img2.png"),
    )


def _required_env(name: str, fallback_name: str | None = None) -> str:
    value = os.getenv(name)
    if not value and fallback_name:
        value = os.getenv(fallback_name)
    if not value:
        expected = f"{name} или {fallback_name}" if fallback_name else name
        raise RuntimeError(f"Не задана переменная окружения {expected}")
    return value


def _resolve_existing_path(path: Path) -> Path:
    for base_dir in (BASE_DIR, PROJECT_DIR):
        candidate = base_dir / path
        if candidate.exists():
            return candidate
    return BASE_DIR / path


def _optional_path(name: str, default: str | None = None) -> Path | None:
    value = os.getenv(name, default or "")
    if not value:
        return None

    path = Path(value)
    if path.is_absolute():
        return path
    return _resolve_existing_path(path)
