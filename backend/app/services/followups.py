"""Conversation follow-ups: recap a dialogue that went quiet and invite the user back.

A dialogue never ends on its own (only /stop or switching advisors closes it), so "finished"
is defined as silence: the user's last message is at least QUIET_AFTER old. The recap is
generated once, stored on the conversation, and delivered by the evening job in place of the
generic question, so the user still receives at most two messages a day.

This is the one place that calls Gemini without a billing grant. The message is the product's
initiative, not a user question, so it is paid by us and bounded by `followup_daily_cap`.
The recap is dialogue content: it goes to the user's own chat only, never to the ops group
and never into an event payload.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.agents import AGENTS
from app.core.config import get_settings
from app.db.models import Conversation, ConversationMessage, User
from app.db.session import SessionFactory
from app.services import agent_chat, conversations, events, users

logger = logging.getLogger(__name__)

# Silence after the last message before a dialogue counts as finished.
QUIET_AFTER = timedelta(hours=20)
# Older dialogues are not dug up: the user has moved on, or already had a follow-up.
MAX_AGE = timedelta(days=7)
# Two user messages at least, so "hello" is never recapped.
MIN_MESSAGES = 4
# At most one follow-up per user in this window, whatever the number of dialogues.
PER_USER_COOLDOWN = timedelta(days=3)
# Generations per job tick; the daily cap applies on top.
BATCH = 20
# Turns given to the summarizer.
HISTORY_LIMIT = 12


async def candidates(session: AsyncSession, now: datetime, limit: int) -> list[Conversation]:
    """Quiet, substantial dialogues whose user has not written anywhere since."""
    last_user = (
        select(
            ConversationMessage.conversation_id.label("conversation_id"),
            func.max(ConversationMessage.created_at).label("at"),
        )
        .where(ConversationMessage.role == "user")
        .group_by(ConversationMessage.conversation_id)
        .subquery()
    )
    other = aliased(Conversation)
    later_user_message = (
        select(ConversationMessage.id)
        .join(other, other.id == ConversationMessage.conversation_id)
        .where(
            other.user_id == Conversation.user_id,
            ConversationMessage.role == "user",
            ConversationMessage.created_at > last_user.c.at,
        )
        .exists()
    )
    prior = aliased(Conversation)
    recent_followup = (
        select(prior.id)
        .where(
            prior.user_id == Conversation.user_id,
            prior.followup_sent_at > now - PER_USER_COOLDOWN,
        )
        .exists()
    )
    result = await session.execute(
        select(Conversation)
        .join(last_user, last_user.c.conversation_id == Conversation.id)
        .join(User, User.id == Conversation.user_id)
        .where(
            Conversation.agent_id.in_(tuple(AGENTS)),
            Conversation.summary == "",
            Conversation.followup_sent_at.is_(None),
            Conversation.message_count >= MIN_MESSAGES,
            last_user.c.at <= now - QUIET_AFTER,
            last_user.c.at >= now - MAX_AGE,
            User.evening_enabled.is_(True),
            User.timezone_source != users.TIMEZONE_SOURCE_DEFAULT,
            ~later_user_message,
            ~recent_followup,
        )
        .order_by(last_user.c.at)
        .limit(limit)
    )
    return list(result.scalars())


async def pending_for_user(session: AsyncSession, user_id: int) -> Conversation | None:
    """A recap waiting to be delivered to this user, newest dialogue first."""
    return await session.scalar(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.summary != "",
            Conversation.followup_sent_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )


async def _generated_today(session: AsyncSession, now: datetime) -> int:
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    counts = await events.count_by_type(session, day_start, now)
    return counts.get(events.CONVERSATION_FOLLOWUP_GENERATED, 0)


async def generate_pending(now: datetime | None = None) -> int:
    """Write recaps for the next batch of quiet dialogues. Returns how many were stored."""
    settings = get_settings()
    if not settings.followup_enabled or not settings.gemini_api_key:
        return 0
    now = now or datetime.now(UTC)

    async with SessionFactory() as session:
        budget = min(BATCH, settings.followup_daily_cap - await _generated_today(session, now))
        if budget <= 0:
            return 0
        rows = await candidates(session, now, budget)
        work = []
        for conversation in rows:
            language = await session.scalar(
                select(User.language).where(User.id == conversation.user_id)
            )
            history = await conversations.list_session_history(
                session, conversation.id, HISTORY_LIMIT
            )
            work.append(
                (conversation.id, conversation.user_id, conversation.agent_id, language, history)
            )

    # No DB session is held across the Gemini calls.
    results = []
    for conversation_id, user_id, agent_id, language, history in work:
        try:
            summary = await agent_chat.summarize_for_followup(agent_id, history, language or "en")
        except Exception as error:
            logger.warning(
                "Follow-up summary failed for conversation %s: %s", conversation_id, error
            )
            continue
        if summary:
            results.append((conversation_id, user_id, agent_id, summary))

    if not results:
        return 0
    async with SessionFactory() as session:
        for conversation_id, user_id, agent_id, summary in results:
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id, Conversation.summary == "")
                .values(summary=summary, updated_at=Conversation.updated_at)
            )
            events.record(
                session,
                events.CONVERSATION_FOLLOWUP_GENERATED,
                user_id,
                agent_id=agent_id,
                conversation_id=str(conversation_id),
            )
        await session.commit()
    return len(results)


async def mark_sent(session: AsyncSession, conversation: Conversation, now: datetime) -> None:
    await session.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(followup_sent_at=now, updated_at=Conversation.updated_at)
    )
    events.record(
        session,
        events.CONVERSATION_FOLLOWUP_SENT,
        conversation.user_id,
        agent_id=conversation.agent_id,
        conversation_id=str(conversation.id),
    )
    await session.refresh(conversation)
