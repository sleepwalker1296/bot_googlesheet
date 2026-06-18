# Telegram-бот учета финансов

Бот помогает быстро фиксировать расходы, доходы и переводы между счетами через Telegram и сохраняет данные в разные листы одной Google Таблицы.

## Возможности

- Главное меню: добавить операцию, последние операции, отмена.
- Учет расходов и доходов.
- Отдельный сценарий переводов между счетами.
- FSM-сценарии aiogram 3.x.
- Inline-кнопки на шагах выбора.
- Валидация суммы: `1250`, `1 250`, `1250.50`, `1250,50`.
- Подтверждение перед записью.
- Команды `/start`, `/cancel`, `/help`, `/last`.
- Запись только в существующие листы клиента без изменения оформления таблицы.

## Структура

```text
bot/
├── main.py
├── config.py
├── keyboards.py
├── states.py
├── handlers/
│   ├── start.py
│   ├── operation.py
│   └── transfer.py
├── services/
│   ├── google_sheets.py
│   └── validators.py
├── utils/
│   └── logger.py
├── requirements.txt
├── .env.example
├── README.md
└── Dockerfile
```

## 1. Создать Telegram-бота через BotFather

1. Откройте Telegram и найдите `@BotFather`.
2. Отправьте команду `/newbot`.
3. Укажите имя бота и username, который заканчивается на `bot`.
4. Скопируйте выданный токен. Он понадобится в переменной `BOT_TOKEN`.

## 2. Создать Google Service Account

1. Откройте [Google Cloud Console](https://console.cloud.google.com/).
2. Создайте проект или выберите существующий.
3. Включите API `Google Sheets API`.
4. Откройте `IAM & Admin` -> `Service Accounts`.
5. Создайте сервисный аккаунт.
6. Внутри аккаунта откройте вкладку `Keys`.
7. Создайте ключ типа `JSON`.
8. Скачайте JSON-файл и положите его рядом с `.env` или укажите абсолютный путь.

## 3. Выдать доступ сервисному аккаунту к Google Таблице

1. Создайте Google Таблицу.
2. Скопируйте ID таблицы из URL.

Пример URL:

```text
https://docs.google.com/spreadsheets/d/GOOGLE_SHEET_ID/edit
```

3. Откройте скачанный JSON сервисного аккаунта.
4. Найдите поле `client_email`.
5. В Google Таблице нажмите `Share` / `Поделиться`.
6. Добавьте `client_email` как редактора.

## 4. Заполнить .env

Создайте файл `.env` рядом с `main.py` или в корне проекта:

```env
BOT_TOKEN=1234567890:telegram_bot_token
GOOGLE_SHEET_ID=google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service-account.json
TIMEZONE=Europe/Moscow
```

Если JSON лежит не рядом с `.env`, укажите абсолютный путь:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=C:\BotTelegram\bot_avito_googleSHEETS\bot\service-account.json
```

## 5. Запуск локально

## Картинка главного меню

По умолчанию бот ищет стартовую картинку здесь:

```text
bot/assets/start.png
bot/assets/img1.png
bot/assets/img2.png
```

Можно указать другой путь в `.env`:

```env
START_IMAGE_FILE=assets/start.png
INCOME_IMAGE_FILE=assets/img1.png
EXPENSE_IMAGE_FILE=assets/img2.png
```

Рекомендуемый размер:

- `1280x720` или `1200x675` для горизонтального баннера.
- Формат `JPG` для фото/баннера или `PNG` для графики с текстом.
- Вес файла желательно до `300-500 КБ`, чтобы меню открывалось быстро.
- Не используйте слишком мелкий текст на картинке: в Telegram она часто открывается в превью.

Если файла нет, бот просто покажет текстовое меню без картинки.

Из папки `C:\BotTelegram\bot_avito_googleSHEETS\bot`:

```powershell
pip install -r requirements.txt
cd ..
python -m bot.main
```

Или из корня проекта:

```powershell
pip install -r bot\requirements.txt
python -m bot.main
```

## 6. Запуск через Docker

Из папки `C:\BotTelegram\bot_avito_googleSHEETS\bot`:

```powershell
docker build -t finance-telegram-bot .
docker run --rm --env-file .env -v ${PWD}\service-account.json:/app/bot/service-account.json finance-telegram-bot
```

Если JSON-файл называется иначе, измените путь в `GOOGLE_SERVICE_ACCOUNT_JSON` и volume.

## 7. Запуск на VPS через Docker Compose

На сервере в корне проекта должны лежать секретные файлы, которые не хранятся в GitHub:

```text
bot/.env
bot/service-account.json
```

В `bot/.env` для compose удобно указать:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=service-account.json
```

Запуск из корня проекта:

```bash
docker compose up -d --build
docker compose logs -f finance-bot
```

Остановка:

```bash
docker compose down
```

## Листы Google Sheets

При запуске бот проверяет, что в Google Таблице уже есть три листа клиента:

- `РС тинькоф`
- `Т-банк Спец карта`
- `Наличка Илья`

Бот не создает дополнительные листы, не перезаписывает заголовки, не замораживает строки и не применяет цвета. Операции добавляются только в выбранный лист счета. Следующая строка определяется по заполненности колонок `A:D`, поэтому колонки с остатком и формулами справа не мешают записи.

Листы счетов ведутся в формате:

```text
Дата | Поступило | Списано | Назначение
```

Перевод пишется двумя строками: списание в лист счета списания и пополнение в лист счета пополнения.
