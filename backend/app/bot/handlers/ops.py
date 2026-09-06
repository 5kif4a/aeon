"""Ops group tooling: `/stats` on demand and scheduled daily/weekly/monthly digests."""

import logging
from datetime import UTC, datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services import events, ops, stats

logger = logging.getLogger(__name__)

STATS_PERIODS = {"7": 7, "30": 30}
DIGEST_TITLES = {"daily": "Daily digest", "weekly": "Weekly digest", "monthly": "Monthly digest"}


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/stats` (today), `/stats 7`, `/stats 30`: only in the ops group or for listed admins."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or not ops.is_ops_request(chat.id, user.id if user else None):
        return
    settings = get_settings()
    now = datetime.now(UTC)
    argument = (context.args or [""])[0]
    if argument in STATS_PERIODS:
        window = stats.last_days_window(now, settings.ops_timezone, STATS_PERIODS[argument])
    else:
        window = stats.today_window(now, settings.ops_timezone)
    async with SessionFactory() as session:
        collected = await stats.collect_stats(session, window, now)
    await context.bot.send_message(
        chat.id,
        stats.format_stats(collected, "Aeon stats"),
        parse_mode="HTML",
        message_thread_id=getattr(update.effective_message, "message_thread_id", None),
    )


async def send_ops_digests(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every 15 minutes; at the configured local hour posts every due digest once."""
    settings = get_settings()
    if not settings.ops_chat_id:
        return
    now = datetime.now(UTC)
    local = stats.local_now(now, settings.ops_timezone)
    for period in stats.digests_due(local, settings.ops_digest_hour):
        today = local.date()
        async with SessionFactory() as session:
            already_sent = await events.last_event_at(
                session, events.OPS_DIGEST_SENT, period=period, date=today.isoformat()
            )
            if already_sent is not None:
                continue
            window = stats.digest_window(period, today, settings.ops_timezone)
            collected = await stats.collect_stats(session, window, now)
        text = stats.format_stats(collected, DIGEST_TITLES[period])
        if not await ops.send(text, ops.THREAD_DIGESTS):
            logger.warning("Ops %s digest was not delivered", period)
            continue
        async with SessionFactory() as session:
            events.record(session, events.OPS_DIGEST_SENT, period=period, date=today.isoformat())
            await session.commit()


def build_ops_handlers() -> list:
    return [CommandHandler("stats", stats_command)]
