"""Durable, agent-specific conversation sessions stored in PostgreSQL."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, ConversationMessage


async def start_session(session: AsyncSession, user_id: int, agent_id: str) -> Conversation:
    await close_active_session(session, user_id)
    conversation = Conversation(user_id=user_id, agent_id=agent_id)
    session.add(conversation)
    await session.flush()
    return conversation


async def close_active_session(
    session: AsyncSession, user_id: int, agent_id: str | None = None
) -> None:
    query = update(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.status == "active",
    )
    if agent_id is not None:
        query = query.where(Conversation.agent_id == agent_id)
    await session.execute(query.values(status="closed", closed_at=datetime.now(UTC)))


async def get_active_history(
    session: AsyncSession, user_id: int, agent_id: str, limit: int
) -> tuple[uuid.UUID | None, list[dict[str, str]]]:
    conversation_id = await get_active_session_id(session, user_id, agent_id)
    if conversation_id is None:
        return None, []
    return conversation_id, await list_session_history(session, conversation_id, limit)


async def get_active_session_id(
    session: AsyncSession, user_id: int, agent_id: str
) -> uuid.UUID | None:
    return await session.scalar(
        select(Conversation.id).where(
            Conversation.user_id == user_id,
            Conversation.agent_id == agent_id,
            Conversation.status == "active",
        )
    )


async def list_session_history(
    session: AsyncSession, conversation_id: uuid.UUID, limit: int
) -> list[dict[str, str]]:
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.position.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    return [{"role": message.role, "text": message.text} for message in messages]


async def list_history(
    session: AsyncSession, user_id: int, agent_id: str, limit: int
) -> list[dict[str, str]]:
    _, history = await get_active_history(session, user_id, agent_id, limit)
    return history


async def append_exchange(
    session: AsyncSession,
    user_id: int,
    agent_id: str,
    user_text: str,
    agent_text: str,
) -> Conversation:
    conversation = await _get_or_create_active_session(session, user_id, agent_id)
    _append_messages(session, conversation, user_text, agent_text)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def append_completed_session(
    session: AsyncSession,
    user_id: int,
    agent_id: str,
    user_text: str,
    agent_text: str,
) -> Conversation:
    now = datetime.now(UTC)
    conversation = Conversation(
        user_id=user_id,
        agent_id=agent_id,
        status="closed",
        closed_at=now,
    )
    session.add(conversation)
    await session.flush()
    _append_messages(session, conversation, user_text, agent_text)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def _get_or_create_active_session(
    session: AsyncSession, user_id: int, agent_id: str
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.agent_id == agent_id,
            Conversation.status == "active",
        )
        .with_for_update()
    )
    if conversation is not None:
        return conversation
    return await start_session(session, user_id, agent_id)


def _append_messages(
    session: AsyncSession,
    conversation: Conversation,
    user_text: str,
    agent_text: str,
) -> None:
    normalized_user_text = str(user_text or "")
    normalized_agent_text = str(agent_text or "")
    first_position = conversation.message_count + 1
    if not conversation.title:
        conversation.title = normalized_user_text.strip()[:160]
    session.add_all(
        [
            ConversationMessage(
                conversation_id=conversation.id,
                position=first_position,
                role="user",
                text=normalized_user_text,
            ),
            ConversationMessage(
                conversation_id=conversation.id,
                position=first_position + 1,
                role="agent",
                text=normalized_agent_text,
            ),
        ]
    )
    conversation.message_count += 2
