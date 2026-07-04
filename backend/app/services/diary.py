import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DiaryEntry

DIARY_LIMIT = 30


async def list_entries(
    session: AsyncSession, user_id: int, limit: int = DIARY_LIMIT
) -> list[DiaryEntry]:
    result = await session.execute(
        select(DiaryEntry)
        .where(DiaryEntry.user_id == user_id)
        .order_by(DiaryEntry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())


async def add_entry(session: AsyncSession, user_id: int, text: str) -> DiaryEntry:
    entry = DiaryEntry(user_id=user_id, text=text[:700])
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete_entry(session: AsyncSession, user_id: int, entry_id: uuid.UUID) -> bool:
    result = await session.execute(
        delete(DiaryEntry).where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
    )
    await session.commit()
    return result.rowcount > 0
