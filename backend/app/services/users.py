from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Goal, User
from app.i18n import normalize_language


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create_user(
    session: AsyncSession, user_id: int, *, name: str = "", language: str = ""
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        settings = get_settings()
        user = User(
            id=user_id,
            name=name[:64],
            language=normalize_language(language),
            reminder_timezone=settings.reminder_tz,
            reminder_hour=settings.reminder_hour,
        )
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


async def life_weekly_notification_candidates(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(
            User.birth_date.is_not(None),
            User.weekly_notifications_enabled.is_(True),
        )
    )
    return list(result.scalars())


async def daily_notification_candidates(
    session: AsyncSession,
) -> list[tuple[User, Goal | None]]:
    result = await session.execute(
        select(User, Goal)
        .outerjoin(
            Goal,
            and_(Goal.user_id == User.id, Goal.status == "active"),
        )
        .where(
            User.birth_date.is_not(None),
            User.daily_notifications_enabled.is_(True),
        )
    )
    return [(user, goal) for user, goal in result.all()]


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


def local_datetime(user: User, now: datetime | None = None) -> datetime:
    try:
        timezone = ZoneInfo(user.reminder_timezone or "UTC")
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("UTC")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(timezone)


def notification_is_due(user: User, now: datetime | None = None) -> bool:
    reminder_hour = user.reminder_hour if user.reminder_hour is not None else 9
    return local_datetime(user, now).hour == min(max(reminder_hour, 0), 23)


async def record_daily_checkin(
    session: AsyncSession, user: User, now: datetime | None = None
) -> int:
    today = local_datetime(user, now).date()
    if user.last_daily_checkin_date == today:
        return user.daily_checkin_streak or 0
    if user.last_daily_checkin_date == today - timedelta(days=1):
        user.daily_checkin_streak = (user.daily_checkin_streak or 0) + 1
    else:
        user.daily_checkin_streak = 1
    user.last_daily_checkin_date = today
    await session.commit()
    await session.refresh(user)
    return user.daily_checkin_streak


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)
