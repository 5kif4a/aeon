from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Goal, User
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


async def users_due_for_life_weekly(session: AsyncSession, today: date) -> list[User]:
    cutoff = today - timedelta(days=7)
    result = await session.execute(
        select(User).where(
            User.birth_date.is_not(None),
            (User.last_life_weekly_date.is_(None))
            | (User.last_life_weekly_date <= cutoff),
        )
    )
    return list(result.scalars())


async def mark_life_weekly_sent(session: AsyncSession, user: User, today: date) -> None:
    user.last_life_weekly_date = today
    await session.commit()


async def users_due_for_daily_notification(
    session: AsyncSession, today: date
) -> list[tuple[User, Goal | None]]:
    weekly_cutoff = today - timedelta(days=7)
    result = await session.execute(
        select(User, Goal)
        .outerjoin(
            Goal,
            and_(Goal.user_id == User.id, Goal.status == "active"),
        )
        .where(
            User.birth_date.is_not(None),
            (User.last_daily_notification_date.is_(None))
            | (User.last_daily_notification_date < today),
            User.last_life_weekly_date.is_not(None),
            User.last_life_weekly_date > weekly_cutoff,
            User.last_life_weekly_date < today,
        )
    )
    return [(user, goal) for user, goal in result.all()]


async def mark_daily_notification_sent(
    session: AsyncSession,
    user: User,
    goal: Goal | None,
    today: date,
) -> None:
    user.last_daily_notification_date = today
    if goal is not None:
        goal.last_reminder_date = today
    await session.commit()


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)
