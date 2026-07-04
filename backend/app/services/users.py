from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.i18n import normalize_language


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create_user(
    session: AsyncSession, user_id: int, *, name: str = "", language: str = ""
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, name=name[:64], language=normalize_language(language))
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, fields: dict) -> User:
    for key, value in fields.items():
        setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


async def all_user_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.id))
    return [row[0] for row in result]


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)
