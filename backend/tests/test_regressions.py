"""Regression tests for the audit fixes: user creation race and session reuse."""

import asyncio

import pytest
from sqlalchemy import delete, func, select

from app.db.models import Conversation, User
from app.db.session import SessionFactory
from app.services import conversations, users

USER_ID = 900_000_201


@pytest.fixture(autouse=True)
async def cleanup_user():
    yield
    async with SessionFactory() as session:
        await session.execute(delete(User).where(User.id == USER_ID))
        await session.commit()


async def test_concurrent_first_requests_create_exactly_one_user():
    async def create() -> int:
        async with SessionFactory() as session:
            user = await users.get_or_create_user(session, USER_ID, name="Racer", language="ru")
            return user.id

    results = await asyncio.gather(*(create() for _ in range(8)))
    assert results == [USER_ID] * 8

    async with SessionFactory() as session:
        count = await session.scalar(select(func.count()).where(User.id == USER_ID))
        user = await session.get(User, USER_ID)
    assert count == 1
    assert user.name == "Racer"
    assert user.language == "ru"


async def test_reselecting_the_same_agent_keeps_the_session():
    async with SessionFactory() as session:
        await users.get_or_create_user(session, USER_ID)
        first = await conversations.start_session(session, USER_ID, "aurelius")
        await session.commit()
        await conversations.append_exchange(session, USER_ID, "aurelius", "Q1", "A1")

        again = await conversations.start_session(session, USER_ID, "aurelius")
        await session.commit()
        assert again.id == first.id
        history = await conversations.list_history(session, USER_ID, "aurelius", limit=8)
        assert history == [{"role": "user", "text": "Q1"}, {"role": "agent", "text": "A1"}]

        switched = await conversations.start_session(session, USER_ID, "jung")
        await session.commit()
        assert switched.id != first.id
        active = await session.scalar(
            select(func.count()).where(
                Conversation.user_id == USER_ID, Conversation.status == "active"
            )
        )
        assert active == 1
        assert await conversations.list_history(session, USER_ID, "aurelius", limit=8) == []
