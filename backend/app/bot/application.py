"""PTB Application assembly: handlers, command menu, and scheduled jobs."""

import logging

from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import Application, ApplicationBuilder

from app.bot.broadcasting import run_queue as run_broadcast_queue
from app.bot.handlers.commands import build_command_handlers
from app.bot.handlers.onboarding import build_onboarding_handler
from app.bot.handlers.ops import build_ops_handlers, send_ops_digests
from app.bot.handlers.payments import build_paysupport_handler
from app.bot.jobs import (
    send_billing_reminders,
    send_daily_notifications,
    send_life_weekly_reviews,
)
from app.core.config import get_settings
from app.services import bot_settings

logger = logging.getLogger(__name__)

# `Update.ALL_TYPES` only lists the update types the installed python-telegram-bot knows.
# `subscription` (Bot API 10.2: Stars subscription canceled / restored / charge failed) is
# newer than PTB 22.x, so it has to be requested by name or Telegram will never send it.
ALLOWED_UPDATES: list[str] = [*Update.ALL_TYPES, "subscription"]


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

    ops_chat_id = get_settings().ops_chat_id
    if ops_chat_id:
        try:
            await application.bot.set_my_commands(
                [BotCommand("stats", "Product stats: today | 7 | 30")],
                scope=BotCommandScopeChat(ops_chat_id),
            )
        except Exception as error:  # the bot may not be in the group yet
            logger.warning("Could not register /stats for the ops chat %s: %s", ops_chat_id, error)


async def _refresh_bot_settings(_context) -> None:
    """Pick up admin-panel edits of prompts/knobs; the API refreshes in-process on write."""
    await bot_settings.refresh_safely()


def build_application() -> Application:
    settings = get_settings()
    builder = ApplicationBuilder().token(settings.bot_token)
    if settings.bot_mode == "webhook":
        builder = builder.updater(None)
    application = builder.build()

    application.add_handler(build_onboarding_handler())
    # Before the plain text handler: while a /paysupport request is open, the next message
    # goes to the ops group instead of the active agent.
    application.add_handler(build_paysupport_handler())
    for handler in (*build_ops_handlers(), *build_command_handlers()):
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

    application.job_queue.run_repeating(
        send_billing_reminders,
        interval=15 * 60,
        first=45,
        name="billing_reminders",
    )

    application.job_queue.run_repeating(
        send_ops_digests,
        interval=15 * 60,
        first=60,
        name="ops_digests",
    )

    # Manual broadcasts from the admin panel: due campaigns are picked up here.
    application.job_queue.run_repeating(
        run_broadcast_queue,
        interval=60,
        first=75,
        name="broadcast_queue",
    )

    application.job_queue.run_repeating(
        _refresh_bot_settings,
        interval=60,
        first=60,
        name="bot_settings_refresh",
    )

    return application
