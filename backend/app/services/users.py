from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Goal, User
from app.i18n import normalize_language
from app.services import events, ops

# Zone provenance values (users.timezone_source). Daily slots stay silent on "default":
# an unknown zone means an unknown night. "language" is a guess good enough to send.
TIMEZONE_SOURCE_DEFAULT = "default"
TIMEZONE_SOURCE_LANGUAGE = "language"
TIMEZONE_SOURCE_DEVICE = "device"
TIMEZONE_SOURCE_MANUAL = "manual"

# Russian speakers span Moscow (UTC+3) to Almaty/Tashkent (UTC+5); UTC+4 keeps the evening
# question between 20:00 and 22:00 for all of them until the Mini App reports a device zone.
# Etc/GMT-4 is the IANA name for UTC+4 (the sign is inverted by convention).
LANGUAGE_TIMEZONES = {"ru": "Etc/GMT-4"}

# Auto-decay thresholds: unanswered morning/evening messages after which each slot goes quiet.
MORNING_SILENCE_LIMIT = 10
EVENING_SILENCE_LIMIT = 24


def default_timezone(language: str) -> tuple[str, str]:
    """Zone and provenance for a user who has not told us where they are."""
    zone = LANGUAGE_TIMEZONES.get(normalize_language(language))
    if zone:
        return zone, TIMEZONE_SOURCE_LANGUAGE
    return get_settings().reminder_tz, TIMEZONE_SOURCE_DEFAULT


def presentable_name(raw: str | None) -> str:
    """A name worth greeting with, or "" (accounts that hide the name send a bare dash)."""
    value = (raw or "").strip()[:64]
    return value if any(ch.isalnum() for ch in value) else ""


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    *,
    name: str = "",
    language: str = "",
    username: str | None = None,
    acquired_from: str = "",
) -> User:
    """Return the user, creating the row on first contact.

    ``username`` is the Telegram handle as seen in this request; ``None`` means unknown
    (callers that only have a chat id), an empty string means the user has none.
    ``acquired_from`` is the sanitized ``/start`` payload; it is stored on creation only.
    """
    user = await session.get(User, user_id)
    if user is not None:
        if username is not None and user.username != username[:64]:
            user.username = username[:64]
            await session.commit()
        return user

    # Concurrent first requests (the Mini App fires several in parallel) must not
    # collide on the primary key: insert-or-ignore, then read whichever row won.
    settings = get_settings()
    timezone, timezone_source = default_timezone(language)
    result = await session.execute(
        insert(User)
        .values(
            id=user_id,
            name=name[:64],
            username=(username or "")[:64],
            language=normalize_language(language),
            reminder_timezone=timezone,
            timezone_source=timezone_source,
            reminder_hour=settings.reminder_hour,
            evening_hour=settings.evening_hour,
            acquired_from=acquired_from[:64],
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    created = result.rowcount == 1
    if created:
        events.record(
            session,
            events.USER_CREATED,
            user_id,
            language=normalize_language(language),
            source=acquired_from[:64],
        )
    await session.commit()
    user = await session.get(User, user_id)
    if user is None:  # pragma: no cover - defensive, the row exists after the upsert
        raise RuntimeError(f"User {user_id} could not be created")
    if created:
        ops.user_created(user)
    return user


_SOURCE_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")


def acquisition_source(args: list[str] | None) -> str:
    """The ``/start <payload>`` argument as a source tag: lowercase, [a-z0-9_-], 64 chars max.

    Anything else (Mini App deep links, junk) becomes an empty string, i.e. organic.
    """
    if not args:
        return ""
    candidate = args[0].strip().lower()[:64]
    if not candidate or any(ch not in _SOURCE_ALLOWED for ch in candidate):
        return ""
    return candidate


async def mark_first_answer(session: AsyncSession, user: User, *, agent_id: str, mode: str) -> bool:
    """Record the first advisor answer ever delivered to this user. Idempotent."""
    if user.first_answer_at is not None:
        return False
    now = datetime.now(UTC)
    user.first_answer_at = now
    created_at = user.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    hours = round((now - created_at).total_seconds() / 3600, 1) if created_at else None
    events.record(
        session,
        events.FIRST_ANSWER_DELIVERED,
        user.id,
        agent_id=agent_id,
        mode=mode,
        hours_since_signup=hours,
        source=user.acquired_from,
    )
    await session.commit()
    return True


async def mark_blocked(session: AsyncSession, user: User, *, source: str) -> None:
    """Telegram answered Forbidden: the user blocked the bot. Idempotent per block."""
    if user.blocked_at is not None:
        return
    user.blocked_at = datetime.now(UTC)
    events.record(session, events.BOT_BLOCKED, user.id, source=source)
    await session.commit()


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
            User.blocked_at.is_(None),
        )
    )
    return list(result.scalars())


async def daily_notification_candidates(
    session: AsyncSession,
) -> list[tuple[User, Goal | None]]:
    """Morning slot: enabled, zone known, not muted by the auto-decay."""
    result = await session.execute(
        select(User, Goal)
        .outerjoin(
            Goal,
            and_(Goal.user_id == User.id, Goal.status == "active"),
        )
        .where(
            User.daily_notifications_enabled.is_(True),
            User.timezone_source != TIMEZONE_SOURCE_DEFAULT,
            User.unanswered_notifications < MORNING_SILENCE_LIMIT,
            User.blocked_at.is_(None),
        )
    )
    return [(user, goal) for user, goal in result.all()]


async def evening_notification_candidates(session: AsyncSession) -> list[User]:
    """Evening slot: enabled, zone known, not muted by the auto-decay."""
    result = await session.execute(
        select(User).where(
            User.evening_enabled.is_(True),
            User.timezone_source != TIMEZONE_SOURCE_DEFAULT,
            User.unanswered_notifications < EVENING_SILENCE_LIMIT,
            User.blocked_at.is_(None),
        )
    )
    return list(result.scalars())


async def users_due_for_life_weekly(session: AsyncSession, today: date) -> list[User]:
    cutoff = today - timedelta(days=7)
    result = await session.execute(
        select(User).where(
            User.birth_date.is_not(None),
            (User.last_life_weekly_date.is_(None)) | (User.last_life_weekly_date <= cutoff),
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
    user.unanswered_notifications = (user.unanswered_notifications or 0) + 1
    if goal is not None:
        goal.last_reminder_date = today
    await session.commit()


async def mark_evening_notification_sent(session: AsyncSession, user: User, today: date) -> None:
    user.last_evening_notification_date = today
    user.unanswered_notifications = (user.unanswered_notifications or 0) + 1
    await session.commit()


async def mark_reaction(session: AsyncSession, user: User) -> None:
    """The user did something (message, button, Mini App open): the decay counter restarts.

    Commits only when there is something to reset, so the hot paths that call it on every
    message do not pay for a write.
    """
    if not user.unanswered_notifications and user.blocked_at is None:
        return
    if user.blocked_at is not None:
        # They wrote to us, so the block is gone; scheduled sends may resume.
        user.blocked_at = None
        events.record(session, events.BOT_UNBLOCKED, user.id)
    user.unanswered_notifications = 0
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
    """Morning slot (and the weekly review, which shares its hour)."""
    reminder_hour = user.reminder_hour if user.reminder_hour is not None else 9
    return local_datetime(user, now).hour == min(max(reminder_hour, 0), 23)


def evening_notification_is_due(user: User, now: datetime | None = None) -> bool:
    evening_hour = user.evening_hour if user.evening_hour is not None else 21
    return local_datetime(user, now).hour == min(max(evening_hour, 0), 23)


def notification_sequence(user: User, today: date) -> int:
    """Position in the text rotation: days since signup, so no two days in a cycle repeat."""
    if user.created_at is None:
        return 0
    return max((today - user.created_at.date()).days, 0)


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


def current_streak(user: User, now: datetime | None = None) -> int:
    """The streak as the user should see it: zero once a day has been skipped.

    The column itself is only rewritten on the next check-in, so it keeps the stale value of
    a streak that already broke; readers show this corrected figure instead.
    """
    if not user.last_daily_checkin_date:
        return 0
    today = local_datetime(user, now).date()
    if user.last_daily_checkin_date < today - timedelta(days=1):
        return 0
    return user.daily_checkin_streak or 0


def checked_in_today(user: User, now: datetime | None = None) -> bool:
    return user.last_daily_checkin_date == local_datetime(user, now).date()


def checkin_week(user: User, now: datetime | None = None) -> list[tuple[date, bool]]:
    """The current local week, Monday to Sunday, each day flagged if it was checked in.

    Only the streak's contiguous run is known (the last check-in date and the count before
    it), so days are derived from that rather than stored; a lapsed streak still shows the
    days it covered until the week turns over. Days after today are never checked.
    """
    today = local_datetime(user, now).date()
    monday = today - timedelta(days=today.weekday())
    checked: set[date] = set()
    last = user.last_daily_checkin_date
    if last is not None:
        for offset in range(min(user.daily_checkin_streak or 0, 7)):
            checked.add(last - timedelta(days=offset))
    return [(day, day in checked) for day in (monday + timedelta(days=i) for i in range(7))]


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(age, 0)
