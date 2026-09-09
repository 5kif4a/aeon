"""Sending side of manual broadcasts: the keyboard, one delivery, and the queue job.

The job runs on the same `JobQueue` as the notifications and works in short bursts: it
never holds a DB session across a Telegram send (recipients are read into detached rows,
sent to, then each result is written back in a fresh session), and it stops when the tick
budget runs out so user-facing handlers keep their share of the event loop.
"""

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import ContextTypes

from app.bot import messaging
from app.core.config import get_settings
from app.db.models import Broadcast, User
from app.db.session import SessionFactory
from app.i18n import t
from app.services import broadcasts, ops, segments

logger = logging.getLogger(__name__)

# Recipients per round trip to the database; one round is ~2 seconds of sending.
BATCH_SIZE = 25
# How long one job tick may work before yielding until the next run.
MAX_TICK_SECONDS = 50


def keyboard(
    language: str, message: broadcasts.Message, category: str
) -> InlineKeyboardMarkup | None:
    """Optional call-to-action, plus a one-tap opt-out on marketing messages."""
    rows = []
    if message.button_text and message.button_url:
        rows.append([InlineKeyboardButton(message.button_text, url=message.button_url)])
    if category == broadcasts.MARKETING:
        rows.append(
            [
                InlineKeyboardButton(
                    t(language, "marketing_unsubscribe_button"), callback_data="marketing:off"
                )
            ]
        )
    return InlineKeyboardMarkup(rows) if rows else None


async def deliver(bot: Bot, user: User, broadcast: Broadcast) -> None:
    """Send one broadcast message. Telegram errors propagate to the caller."""
    message = broadcasts.render(broadcast, user.language)
    await messaging.send_chunked(
        bot,
        user.id,
        message.text,
        keyboard(user.language, message, broadcast.category),
        markdown=broadcast.markdown,
    )


async def _send_one(bot: Bot, broadcast: Broadcast, user: User) -> tuple[str, str] | None:
    """Send to one recipient and classify the outcome as (status, error).

    Returns None on `RetryAfter`: the row stays pending and the whole broadcast pauses until
    the next tick, which is what keeps us inside Telegram's limits.
    """
    try:
        await deliver(bot, user, broadcast)
        return "sent", ""
    except RetryAfter as error:
        logger.warning("Broadcast %s throttled: %s", broadcast.id, error)
        return None
    except Forbidden as error:
        # The user blocked the bot or deleted the chat: not a failure worth retrying.
        return "blocked", str(error)
    except TelegramError as error:
        return "failed", str(error)
    except Exception as error:  # network/runtime hiccup: keep the campaign going
        logger.warning("Broadcast %s failed for %s: %s", broadcast.id, user.id, error)
        return "failed", str(error)


async def run_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Work on every due broadcast until the tick budget is spent.

    One broadcast's failure is logged and must not starve the others in the same tick.
    """
    rate = max(get_settings().broadcast_rate_per_second, 1)
    deadline = time.monotonic() + MAX_TICK_SECONDS

    async with SessionFactory() as session:
        due = await broadcasts.due_broadcasts(session)
        ids = [broadcast.id for broadcast in due]

    for broadcast_id in ids:
        if time.monotonic() > deadline:
            return
        try:
            await _run_one(context.bot, broadcast_id, rate, deadline)
        except Exception as error:
            logger.exception("Broadcast %s: tick aborted: %s", broadcast_id, error)


async def _run_one(bot: Bot, broadcast_id: uuid.UUID, rate: int, deadline: float) -> None:
    async with SessionFactory() as session:
        row = await broadcasts.get_broadcast(session, broadcast_id)
        if row is None or row.broadcast.status not in broadcasts.RUNNABLE:
            return
        broadcast = row.broadcast
        first_run = broadcast.status == broadcasts.SCHEDULED
        try:
            total = await broadcasts.materialize(session, broadcast)
        except (broadcasts.BroadcastError, segments.SegmentError) as error:
            # The audience no longer resolves (segment deleted, a filter this build rejects):
            # park the broadcast instead of raising on every tick.
            broadcast.status = broadcasts.FAILED
            broadcast.finished_at = datetime.now(UTC)
            await session.commit()
            ops.broadcast_failed(broadcast, str(error))
            return
        if total is None:
            # Canceled between our read and the commit; the admin's decision stands.
            return
        if first_run:
            ops.broadcast_started(broadcast, total)

    while time.monotonic() < deadline:
        async with SessionFactory() as session:
            # Re-read the status every round: the panel may have canceled the send.
            current = await session.get(Broadcast, broadcast_id)
            if current is None or current.status != broadcasts.SENDING:
                return
            batch = await broadcasts.next_pending(session, broadcast_id, BATCH_SIZE)
        if not batch:
            break
        for delivery_id, user in batch:
            outcome = await _send_one(bot, current, user)
            if outcome is None:
                return
            # Written per message, in its own short session: a restart mid-batch then
            # re-sends at most one message instead of the whole batch.
            async with SessionFactory() as session:
                await broadcasts.mark_deliveries(session, [(delivery_id, *outcome)])
            await asyncio.sleep(1 / rate)
            if time.monotonic() > deadline:
                return

    async with SessionFactory() as session:
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast is None or broadcast.status != broadcasts.SENDING:
            return
        pending = await broadcasts.refresh_counters(session, broadcast)
        if pending == 0:
            await broadcasts.finish(session, broadcast)
            ops.broadcast_finished(broadcast)
