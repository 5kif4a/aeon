from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Goal


async def get_active_goal(session: AsyncSession, user_id: int) -> Goal | None:
    result = await session.execute(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.status == "active")
        .order_by(Goal.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def set_goal(session: AsyncSession, user_id: int, text: str) -> Goal:
    existing = await get_active_goal(session, user_id)
    if existing is not None:
        existing.status = "closed"
        existing.closed_at = datetime.now(UTC)
    goal = Goal(user_id=user_id, text=text[:512])
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


async def close_active_goal(session: AsyncSession, user_id: int) -> Goal | None:
    goal = await get_active_goal(session, user_id)
    if goal is None:
        return None
    goal.status = "closed"
    goal.closed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(goal)
    return goal


async def goals_due_for_reminder(session: AsyncSession, today: date) -> list[Goal]:
    result = await session.execute(
        select(Goal)
        .options(joinedload(Goal.user))
        .where(
            Goal.status == "active",
            (Goal.last_reminder_date.is_(None)) | (Goal.last_reminder_date < today),
        )
    )
    return list(result.scalars())


async def mark_reminded(session: AsyncSession, goal: Goal, today: date) -> None:
    goal.last_reminder_date = today
    await session.commit()
