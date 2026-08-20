"""PTB Application assembly: handlers, command menu, and scheduled jobs."""

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from app.bot.handlers.commands import build_command_handlers
from app.bot.handlers.onboarding import build_onboarding_handler
from app.bot.jobs import send_daily_notifications, send_life_weekly_reviews
from app.core.config import get_settings


async def configure_commands(application: Application) -> None:
    english = [
        BotCommand("start", "Open Aeon"),
        BotCommand("agents", "Choose an advisor"),
        BotCommand("council", "Ask the Council of Three"),
        BotCommand("settings", "Notifications and language"),
        BotCommand("subscribe", "Get Aeon Pro"),
        BotCommand("paysupport", "Payment support"),
    ]
    russian = [
        BotCommand("start", "Открыть Aeon"),
        BotCommand("agents", "Выбрать советника"),
        BotCommand("council", "Спросить Совет трёх"),
        BotCommand("settings", "Уведомления и язык"),
        BotCommand("subscribe", "Подключить Aeon Pro"),
        BotCommand("paysupport", "Помощь с оплатой"),
    ]
    await application.bot.set_my_commands(english)
    await application.bot.set_my_commands(russian, language_code="ru")


def build_application() -> Application:
    settings = get_settings()
    builder = ApplicationBuilder().token(settings.bot_token)
    if settings.bot_mode == "webhook":
        builder = builder.updater(None)
    application = builder.build()

    application.add_handler(build_onboarding_handler())
    for handler in build_command_handlers():
        application.add_handler(handler)

    application.job_queue.run_repeating(
        send_life_weekly_reviews,
        interval=15 * 60,
        first=15,
        name="life_weekly_reviews",
    )

    application.job_queue.run_repeating(
        send_daily_notifications,
        interval=15 * 60,
        first=30,
        name="daily_notifications",
    )

    return application
