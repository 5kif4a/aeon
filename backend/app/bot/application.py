"""PTB Application assembly: handlers + job queue."""

import datetime
from zoneinfo import ZoneInfo

from telegram.ext import Application, ApplicationBuilder

from app.bot.handlers.commands import build_command_handlers
from app.bot.handlers.onboarding import build_onboarding_handler
from app.bot.jobs import send_daily_notifications, send_life_weekly_reviews
from app.core.config import get_settings


def build_application() -> Application:
    settings = get_settings()
    builder = ApplicationBuilder().token(settings.bot_token)
    if settings.bot_mode == "webhook":
        builder = builder.updater(None)
    application = builder.build()

    application.add_handler(build_onboarding_handler())
    for handler in build_command_handlers():
        application.add_handler(handler)

    application.job_queue.run_daily(
        send_life_weekly_reviews,
        time=datetime.time(hour=settings.life_weekly_hour, tzinfo=ZoneInfo(settings.reminder_tz)),
        name="life_weekly_reviews",
    )
    application.job_queue.run_once(
        send_life_weekly_reviews,
        when=15,
        name="life_weekly_reviews_startup",
    )

    application.job_queue.run_daily(
        send_daily_notifications,
        time=datetime.time(hour=settings.reminder_hour, tzinfo=ZoneInfo(settings.reminder_tz)),
        name="daily_notifications",
    )
    application.job_queue.run_once(
        send_daily_notifications,
        when=30,
        name="daily_notifications_startup",
    )

    return application
