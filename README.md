# Бот «Путь к форме»

![CI](https://github.com/Victor-git-19/fitness_motivation_bot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![python-telegram-bot](https://img.shields.io/badge/PTB-22.x-26A5E4?logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

Async-бот на python-telegram-bot 20+ с главным меню, бесплатной 7-дневкой и оффером 30-дневной программы.

## Запуск
- Требуется Python 3.10+ (проект использует venv).
- Установить зависимости: `pip install -r requirements.txt` (включая extra для JobQueue)
- Настроить `.env`:
  ```
  telegram_token=ВАШ_ТОКЕН
  ```
- Старт: `python -m app.main`

## Что умеет
- Главное меню (ReplyKeyboard): «Старт программы (7 дней)», «О проекте», «Обратная связь», «Перейти к полной программе (30 дней)».
- /start: приветствие + показ меню.
- «Старт программы (7 дней)»: сразу шлёт День 1, затем Дни 2–7 приходят автоматически каждые 24 часа через JobQueue.
- «О проекте»: краткое описание 7-дневки.
- «Обратная связь»: контакт автора.
- «Перейти к полной программе (30 дней)»: продающий текст 30-дневки.
- Триггер «Хочу 30 дней» (регистр не важен): ответ с инструкцией связаться с автором.
- Фолбэк: сообщение о неизвестной команде и повторное показ меню.
- Повторный запуск 7-дневки блокируется, пока активна текущая рассылка (можно запустить заново после её завершения или перезапуска бота).

## Как работает рассылка 7 дней
- Пользователь нажимает «Старт программы (7 дней)».
- День 1 отправляется сразу из `start_program`.
- Для Дней 2–7 создаются задачи JobQueue с задержкой `day_index * DAY_DELAY_SECONDS` (по умолчанию 24 часа). Задачи хранятся в `context.chat_data["program_jobs"]`, чтобы можно было снять старые при повторном старте.
- Колбэк `send_day_job` вытаскивает `chat_id` и `day_index` из данных задачи и вызывает `send_day_program`, который форматирует текст дня и шлёт его.
- Если JobQueue не доступен (зависимость не установлена), бот предупредит: День 1 отправится, но планирование Дней 2–7 не настроится.

## Настройка/дебаг
- Хотите протестировать быстрее — временно уменьшите `DAY_DELAY_SECONDS` в `app/main.py`.
- Логи пишутся в stdout (logging.basicConfig level=INFO).

## Docker
- Сборка: `docker build -t fitness-bot .`
- Запуск: `docker run --rm -e telegram_token=ВАШ_ТОКЕН fitness-bot`
- docker-compose не требуется: сервис один, внешние зависимости отсутствуют.

## Структура
- `app/main.py` — вся логика бота (handlers, тексты, JobQueue).
- `app/config.py` — загрузка настроек из `.env`.
- `requirements.txt` — зависимости.
