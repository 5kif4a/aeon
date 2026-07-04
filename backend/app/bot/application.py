"""PTB Application assembly: handlers + job queue."""

import datetime
from zoneinfo import ZoneInfo

from telegram.ext import Application, ApplicationBuilder

from app.bot.handlers.commands import build_command_handlers
from app.bot.handlers.onboarding import build_onboarding_handler
from app.bot.jobs import remind_due_goals
from app.core.config import get_settings


def build_application() -> Application:
    settings = get_settings()
    builder = ApplicationBuilder().token(settings.telegram_bot_token)
    if settings.bot_mode == "webhook":
        builder = builder.updater(None)
    application = builder.build()

    application.add_handler(build_onboarding_handler())
    for handler in build_command_handlers():
        application.add_handler(handler)

    application.job_queue.run_daily(
        remind_due_goals,
        time=datetime.time(hour=settings.reminder_hour, tzinfo=ZoneInfo(settings.reminder_tz)),
        name="goal_reminders",
    )
    # Catch up after restarts: also check once shortly after startup.
    application.job_queue.run_once(remind_due_goals, when=15, name="goal_reminders_startup")

    return application
