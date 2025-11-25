from __future__ import annotations

import logging
from typing import Dict, List

from telegram import Bot, ReplyKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from app.config import settings
from app.constants import (AUTHOR_CONTACT, DAY_DELAY_SECONDS,
                           MAIN_MENU_BUTTONS, PROGRAM_DAYS)


logger = logging.getLogger(__name__)


def main_menu_markup() -> ReplyKeyboardMarkup:
    """Строит клавиатуру главного меню с фиксированными кнопками."""
    return ReplyKeyboardMarkup(
        [
            [MAIN_MENU_BUTTONS[0]],
            [MAIN_MENU_BUTTONS[1], MAIN_MENU_BUTTONS[2]],
            [MAIN_MENU_BUTTONS[3]],
        ],
        resize_keyboard=True,
    )


def format_day_message(day_index: int, day: Dict[str, str]) -> str:
    """Формирует текст программы дня для отправки пользователю."""
    parts: List[str] = [
        day["title"],
        "",
        "Питание",
        "",
        day["nutrition"],
        "",
        "Тренировка",
        "",
        day["workout"],
        "",
        "Шаги",
        "",
        day["steps"],
        "",
        "Привычка дня",
        "",
        day["habit"],
        "",
        "Мотивация",
        "",
        day["motivation"],
    ]

    return "\n".join(parts)


async def send_day_program(
    chat_id: int,
    bot: Bot,
    day_index: int,
) -> None:
    """Отправляет конкретный день программы по индексу."""
    if day_index >= len(PROGRAM_DAYS):
        logger.warning("Запрошен несуществующий день программы: %s", day_index)
        return

    day = PROGRAM_DAYS[day_index]
    text = format_day_message(day_index, day)
    await bot.send_message(chat_id=chat_id, text=text)
    logger.info("Отправлен день %s для чата %s", day_index + 1, chat_id)


async def send_day_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Колбэк JobQueue: достаёт данные задачи и шлёт нужный день."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    day_index = data.get("day_index")
    if chat_id is None or day_index is None:
        logger.warning("Нет данных для задачи отправки дня: %s", context.job)
        return

    await send_day_program(chat_id=chat_id, bot=context.bot,
                           day_index=day_index)

    if (
        context.chat_data is not None
        and day_index is not None
        and day_index >= len(PROGRAM_DAYS) - 1
    ):
        context.chat_data["program_active"] = False
        context.chat_data["program_jobs"] = []
        logger.info("Программа завершена для чата %s", chat_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start: приветствует и показывает главное меню."""
    if update.message is None:
        return

    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    greeting = (
        "Привет! Это бот программы «Путь к форме».\n\n"
        "Запускай бесплатную 7-дневную разминку: питание,"
        " тренировки, шаги и привычки "
        "без жёстких диет. Выбирай действие в меню ниже."
    )
    await update.message.reply_text(greeting, reply_markup=main_menu_markup())
    logger.info("/start для чата %s", chat_id)


async def start_program(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает 7-дневку: День 1 сразу, остальные — через JobQueue."""
    if update.message is None or update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    if context.chat_data.get("program_active"):
        await update.message.reply_text(
            "Программа уже запущена. Дожидайся ежедневных сообщений или дождись окончания, "
            "чтобы запустить заново.",
            reply_markup=main_menu_markup(),
        )
        logger.info("Попытка повторного запуска программы в чате %s отклонена", chat_id)
        return

    for job in context.chat_data.get("program_jobs", []):
        job.schedule_removal()
        logger.info("Снята старая задача %s для чата %s", job.name, chat_id)

    await update.message.reply_text(
        "Запускаем бесплатную 7-дневную программу! Вот твой День 1:",
        reply_markup=main_menu_markup(),
    )
    await send_day_program(chat_id=chat_id, bot=context.bot, day_index=0)

    job_queue = context.job_queue
    if job_queue is None:
        logger.error(
            "JobQueue недоступен. Установите зависимость: pip install \"python-telegram-bot[job-queue]\""
        )
        await update.message.reply_text(
            "Не удалось запланировать рассылку дней 2–7: нужна зависимость "
            "python-telegram-bot[job-queue]. День 1 уже отправлен.",
            reply_markup=main_menu_markup(),
        )
        return

    jobs = []
    for day_index in range(1, len(PROGRAM_DAYS)):
        job = job_queue.run_once(
            send_day_job,
            when=day_index * DAY_DELAY_SECONDS,
            data={"chat_id": chat_id, "day_index": day_index},
            chat_id=chat_id,
            name=f"program_{chat_id}_{day_index}",
        )
        jobs.append(job)
        logger.info(
            "Запланирован день %s для чата %s через %s секунд",
            day_index + 1,
            chat_id,
            day_index * DAY_DELAY_SECONDS,
        )

    context.chat_data["program_jobs"] = jobs
    context.chat_data["program_active"] = True

    await update.message.reply_text(
        "Готово! Дни 2–7 будут прилетать раз в сутки. Удачи!",
        reply_markup=main_menu_markup(),
    )
    logger.info("Запуск программы завершён для чата %s", chat_id)


async def about_project(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Рассказывает кратко о 7-дневной программе."""
    if update.message is None:
        return

    text = (
        "Мини-программа «Путь к форме» — мягкий 7-дневный старт.\n\n"
        "Что тебя ждёт:\n"
        " • Питание без диет и запретов\n"
        " • Короткие тренировки дома\n"
        " • Шаги и лёгкая активность\n"
        " • Простые привычки на каждый день\n"
        " • Мотивация без насилия над собой\n\n"
        "Цель — включиться в процесс и почувствовать первые изменения."
    )
    await update.message.reply_text(text, reply_markup=main_menu_markup())


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет контакты для обратной связи."""
    if update.message is None:
        return

    text = (
        "Есть вопросы по упражнениям, питанию или программе?\n"
        f"Напиши автору: {AUTHOR_CONTACT}\n"
        "Кратко расскажи, что хочется уточнить — так ответ будет"
        " быстрее и точнее."
    )
    await update.message.reply_text(text, reply_markup=main_menu_markup())


async def full_program(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает продающий текст 30-дневной программы."""
    if update.message is None:
        return

    text = (
        "Полная версия «Путь к форме: 30 дней»:\n"
        " • 30 дней привычек\n"
        " • 5 тренировок в неделю (20–30 минут)\n"
        " • Простое питание, без весов\n"
        " • Прогрессия в обучении\n"
        " • Поддержка\n"
        " • Трекинг шагов и выполнения\n\n"
        f"Хочешь дальше? Напиши «Хочу 30 дней» или пиши автору {AUTHOR_CONTACT}."
    )
    await update.message.reply_text(text, reply_markup=main_menu_markup())


async def handle_want_full(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> None:
    """Реакция на триггер «Хочу 30 дней»."""
    if update.message is None:
        return

    text = (
        "Отлично, что готов продолжать! Напиши автору, он расскажет про"
        " формат и оплату:\n"
        f"{AUTHOR_CONTACT}\n\n"
        "Если хочешь — отправь ему сообщение «Хочу 30 дней», и он"
        " ответит с деталями."
    )
    await update.message.reply_text(text, reply_markup=main_menu_markup())


async def default_response(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на неизвестные сообщения с показом меню."""
    if update.message is None:
        return

    await update.message.reply_text(
        "Я пока не знаю такой команды, воспользуйся, пожалуйста, меню ниже.",
        reply_markup=main_menu_markup(),
    )


async def text_router(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    """Роутер текстовых сообщений по кнопкам, триггеру и фолбэку."""
    if update.message is None:
        return

    user_text = update.message.text or ""
    lowered = user_text.lower().strip()

    if lowered == MAIN_MENU_BUTTONS[0].lower():
        await start_program(update, context)
    elif lowered == MAIN_MENU_BUTTONS[1].lower():
        await about_project(update, context)
    elif lowered == MAIN_MENU_BUTTONS[2].lower():
        await feedback(update, context)
    elif lowered == MAIN_MENU_BUTTONS[3].lower():
        await full_program(update, context)
    elif "хочу 30 дней" in lowered:
        await handle_want_full(update, context)
    else:
        await default_response(update, context)
    logger.info("Получен текст \"%s\" в чате %s",
                lowered,
                update.effective_chat.id if update.effective_chat else "unknown")


def run() -> None:
    """Точка входа: создаёт приложение и запускает лонгполлинг."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    application = ApplicationBuilder().token(settings.telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
    )

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()
