"""Audiences for manual broadcasts: saved filters (dynamic) and pinned id lists (static).

A dynamic segment stores a small JSON object of conditions, validated against
`FILTER_SPECS` and translated into SQL here; it is re-evaluated every time the segment is
counted or sent to, so a broadcast always reaches the current membership. A static segment
stores explicit user ids in `segment_members`.

Filter keys are camelCase because the same JSON travels to the panel unchanged. Unknown or
empty values are rejected rather than ignored: a silently dropped condition would send a
campaign to the wrong people.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, Select, case, delete, exists, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import AGENTS
from app.db.models import (
    BillingPayment,
    Conversation,
    DailyUsage,
    SegmentMember,
    User,
    UserSegment,
)
from app.i18n import SUPPORTED_LANGUAGES
from app.services import events

PLANS = ("Free", "Trial", "Pro")
GENDERS = ("male", "female", "other")
MAX_STATIC_MEMBERS = 50_000
SAMPLE_SIZE = 10


class SegmentError(ValueError):
    """Malformed filter definition or unsaved segment reference."""


@dataclass(frozen=True)
class FilterSpec:
    key: str
    kind: str  # enum | bool | int | ids
    description: str
    options: tuple[str, ...] = ()


FILTER_SPECS: tuple[FilterSpec, ...] = (
    FilterSpec("plans", "enum", "Effective plan right now", PLANS),
    FilterSpec("languages", "enum", "Interface language", SUPPORTED_LANGUAGES),
    FilterSpec("genders", "enum", "Gender from onboarding", GENDERS),
    FilterSpec("countries", "ids", "Country from onboarding (exact names)"),
    FilterSpec("agents", "enum", "Has talked to any of these agents", tuple(AGENTS)),
    FilterSpec("onboarded", "bool", "Finished onboarding (birth date set)"),
    FilterSpec("hasPaid", "bool", "Has at least one paid Stars charge"),
    FilterSpec("trialUsed", "bool", "Has ever started the trial"),
    FilterSpec("proAutoRenew", "bool", "Pro subscription renews automatically"),
    FilterSpec("dailyNotificationsEnabled", "bool", "Daily notifications are on"),
    FilterSpec("marketingEnabled", "bool", "Has not opted out of marketing"),
    FilterSpec("signedUpWithinDays", "int", "Signed up in the last N days"),
    FilterSpec("signedUpBeforeDays", "int", "Signed up more than N days ago"),
    FilterSpec("activeWithinDays", "int", "Asked something or used the app in the last N days"),
    FilterSpec("inactiveForDays", "int", "Nothing at all in the last N days"),
    FilterSpec("questionsMin", "int", "At least this many questions in total"),
    FilterSpec("questionsMax", "int", "At most this many questions in total"),
    FilterSpec("streakMin", "int", "Daily check-in streak of at least"),
    FilterSpec("userIds", "ids", "Only these user ids"),
)

FILTERS_BY_KEY = {spec.key: spec for spec in FILTER_SPECS}


def validate_filters(filters: dict) -> dict:
    """Return the normalized filter object, raising on anything the SQL builder would drop."""
    if not isinstance(filters, dict):
        raise SegmentError("Filters must be an object")
    unknown = sorted(set(filters) - set(FILTERS_BY_KEY))
    if unknown:
        raise SegmentError(f"Unknown filters: {', '.join(unknown)}")
    clean: dict = {}
    for key, value in filters.items():
        spec = FILTERS_BY_KEY[key]
        if value is None or value == [] or value == "":
            continue
        if spec.kind == "bool":
            if not isinstance(value, bool):
                raise SegmentError(f"{key} must be true or false")
            clean[key] = value
        elif spec.kind == "int":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SegmentError(f"{key} must be a non-negative whole number")
            clean[key] = value
        elif spec.kind == "enum":
            values = _as_list(key, value)
            invalid = sorted(set(values) - set(spec.options))
            if invalid:
                raise SegmentError(f"{key}: unsupported values {', '.join(invalid)}")
            clean[key] = values
        else:  # ids: free-form strings, or user ids for `userIds`
            values = _as_list(key, value)
            if key == "userIds":
                try:
                    clean[key] = [int(item) for item in values]
                except (TypeError, ValueError) as error:
                    raise SegmentError("userIds must be whole numbers") from error
            else:
                clean[key] = [str(item).strip() for item in values if str(item).strip()]
    return clean


def _as_list(key: str, value) -> list:
    if isinstance(value, str | int | float):
        return [value]
    if isinstance(value, list):
        return value
    raise SegmentError(f"{key} must be a value or a list of values")


def _plan_expression(now: datetime) -> ColumnElement:
    return case(
        (User.pro_expires_at > now, "Pro"),
        (User.trial_expires_at > now, "Trial"),
        else_="Free",
    )


def _questions_total() -> ColumnElement:
    return (
        select(
            func.coalesce(
                func.sum(
                    DailyUsage.prompt_questions
                    + DailyUsage.rag_questions
                    + DailyUsage.council_questions
                ),
                0,
            )
        )
        .where(DailyUsage.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )


def _active_since(cutoff: datetime) -> ColumnElement:
    """True when the user asked something or opened a dialogue after `cutoff`."""
    used = exists().where(DailyUsage.user_id == User.id, DailyUsage.usage_date >= cutoff.date())
    talked = exists().where(Conversation.user_id == User.id, Conversation.updated_at >= cutoff)
    return used | talked


def build_conditions(filters: dict, now: datetime | None = None) -> list[ColumnElement]:
    """Translate a validated filter object into AND-combined SQL conditions on `users`."""
    current = now or datetime.now(UTC)
    clean = validate_filters(filters)
    conditions: list[ColumnElement] = []
    for key, value in clean.items():
        if key == "plans":
            conditions.append(_plan_expression(current).in_(value))
        elif key == "languages":
            conditions.append(User.language.in_(value))
        elif key == "genders":
            conditions.append(func.lower(User.gender).in_([item.lower() for item in value]))
        elif key == "countries":
            conditions.append(func.lower(User.country).in_([item.lower() for item in value]))
        elif key == "agents":
            conditions.append(
                exists().where(Conversation.user_id == User.id, Conversation.agent_id.in_(value))
            )
        elif key == "onboarded":
            conditions.append(User.birth_date.is_not(None) if value else User.birth_date.is_(None))
        elif key == "hasPaid":
            paid = exists().where(
                BillingPayment.user_id == User.id, BillingPayment.status == "paid"
            )
            conditions.append(paid if value else ~paid)
        elif key == "trialUsed":
            conditions.append(
                User.trial_started_at.is_not(None) if value else User.trial_started_at.is_(None)
            )
        elif key == "proAutoRenew":
            conditions.append(User.pro_auto_renew.is_(value))
        elif key == "dailyNotificationsEnabled":
            conditions.append(User.daily_notifications_enabled.is_(value))
        elif key == "marketingEnabled":
            conditions.append(User.marketing_enabled.is_(value))
        elif key == "signedUpWithinDays":
            conditions.append(User.created_at >= current - timedelta(days=value))
        elif key == "signedUpBeforeDays":
            conditions.append(User.created_at < current - timedelta(days=value))
        elif key == "activeWithinDays":
            conditions.append(_active_since(current - timedelta(days=value)))
        elif key == "inactiveForDays":
            conditions.append(~_active_since(current - timedelta(days=value)))
        elif key == "questionsMin":
            conditions.append(_questions_total() >= value)
        elif key == "questionsMax":
            conditions.append(_questions_total() <= value)
        elif key == "streakMin":
            conditions.append(func.coalesce(User.daily_checkin_streak, 0) >= value)
        elif key == "userIds":
            conditions.append(User.id.in_(value))
    return conditions


@dataclass
class Audience:
    """A resolved audience definition, ready to be counted or iterated."""

    kind: str  # dynamic | static
    filters: dict
    segment_id: uuid.UUID | None = None
    # Marketing broadcasts skip users who opted out; service ones do not.
    respect_opt_out: bool = False

    def select_users(self, now: datetime | None = None) -> Select:
        query = select(User)
        if self.kind == "static":
            if self.segment_id is None:
                raise SegmentError("A static audience needs a saved segment")
            query = query.join(
                SegmentMember,
                (SegmentMember.user_id == User.id) & (SegmentMember.segment_id == self.segment_id),
            )
        else:
            conditions = build_conditions(self.filters, now)
            if conditions:
                query = query.where(*conditions)
        if self.respect_opt_out:
            query = query.where(User.marketing_enabled.is_(True))
        return query


async def count_audience(
    session: AsyncSession, audience: Audience, now: datetime | None = None
) -> int:
    query = audience.select_users(now).with_only_columns(func.count(User.id)).order_by(None)
    return int(await session.scalar(query) or 0)


async def audience_by_language(
    session: AsyncSession, audience: Audience, now: datetime | None = None
) -> dict[str, int]:
    query = (
        audience.select_users(now)
        .with_only_columns(User.language, func.count(User.id))
        .group_by(User.language)
        .order_by(None)
    )
    return {language or "": int(count) for language, count in await session.execute(query)}


async def audience_sample(
    session: AsyncSession, audience: Audience, limit: int = SAMPLE_SIZE, now: datetime | None = None
) -> list[User]:
    query = audience.select_users(now).order_by(User.created_at.desc()).limit(limit)
    return list(await session.scalars(query))


# --- stored segments ---------------------------------------------------------------------


def _dynamic_filters(filters: dict) -> dict:
    """A saved dynamic segment needs at least one condition: `{}` would mean everyone."""
    clean = validate_filters(filters)
    if not clean:
        raise SegmentError("Add at least one condition; an empty segment would match everyone")
    return clean


@dataclass
class SegmentRow:
    segment: UserSegment
    size: int
    member_count: int


def audience_for(segment: UserSegment, *, respect_opt_out: bool = False) -> Audience:
    return Audience(
        kind=segment.kind,
        filters=dict(segment.filters or {}),
        segment_id=segment.id,
        respect_opt_out=respect_opt_out,
    )


async def _describe(
    session: AsyncSession, segment: UserSegment, now: datetime | None = None
) -> SegmentRow:
    member_count = int(
        await session.scalar(
            select(func.count())
            .select_from(SegmentMember)
            .where(SegmentMember.segment_id == segment.id)
        )
        or 0
    )
    try:
        size = await count_audience(session, audience_for(segment), now)
    except SegmentError:
        # A definition saved by an older build; the panel shows it so it can be fixed.
        size = 0
    return SegmentRow(segment=segment, size=size, member_count=member_count)


async def list_segments(session: AsyncSession, now: datetime | None = None) -> list[SegmentRow]:
    segments = list(await session.scalars(select(UserSegment).order_by(UserSegment.name)))
    return [await _describe(session, segment, now) for segment in segments]


async def get_segment(session: AsyncSession, segment_id: uuid.UUID) -> SegmentRow | None:
    segment = await session.get(UserSegment, segment_id)
    if segment is None:
        return None
    return await _describe(session, segment)


async def create_segment(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    kind: str,
    filters: dict,
    user_ids: list[int],
    actor_id: int,
) -> SegmentRow:
    segment = UserSegment(
        name=name.strip(),
        description=description.strip(),
        kind=kind,
        filters=_dynamic_filters(filters) if kind == "dynamic" else {},
        created_by=actor_id,
    )
    session.add(segment)
    await session.flush()
    if kind == "static":
        await _replace_members(session, segment.id, user_ids)
    events.record(
        session,
        events.SEGMENT_CHANGED,
        actor_id,
        segment_id=str(segment.id),
        action="created",
        kind=kind,
    )
    await session.commit()
    # `updated_at` is expired by the commit (server-side onupdate); reload before reading it.
    await session.refresh(segment)
    return await _describe(session, segment)


async def update_segment(
    session: AsyncSession,
    segment_id: uuid.UUID,
    *,
    name: str,
    description: str,
    kind: str,
    filters: dict,
    user_ids: list[int],
    actor_id: int,
) -> SegmentRow | None:
    segment = await session.get(UserSegment, segment_id)
    if segment is None:
        return None
    segment.name = name.strip()
    segment.description = description.strip()
    segment.kind = kind
    segment.filters = _dynamic_filters(filters) if kind == "dynamic" else {}
    if kind == "static":
        await _replace_members(session, segment.id, user_ids)
    else:
        await session.execute(delete(SegmentMember).where(SegmentMember.segment_id == segment.id))
    events.record(
        session,
        events.SEGMENT_CHANGED,
        actor_id,
        segment_id=str(segment.id),
        action="updated",
        kind=kind,
    )
    await session.commit()
    await session.refresh(segment)
    return await _describe(session, segment)


async def delete_segment(session: AsyncSession, segment_id: uuid.UUID, *, actor_id: int) -> bool:
    segment = await session.get(UserSegment, segment_id)
    if segment is None:
        return False
    await session.delete(segment)
    events.record(
        session, events.SEGMENT_CHANGED, actor_id, segment_id=str(segment_id), action="deleted"
    )
    await session.commit()
    return True


async def segment_member_ids(session: AsyncSession, segment_id: uuid.UUID) -> list[int]:
    return list(
        await session.scalars(
            select(SegmentMember.user_id)
            .where(SegmentMember.segment_id == segment_id)
            .order_by(SegmentMember.user_id)
        )
    )


async def _replace_members(
    session: AsyncSession, segment_id: uuid.UUID, user_ids: list[int]
) -> None:
    """Pin exactly these ids into a static segment; ids without a user row are dropped."""
    if len(user_ids) > MAX_STATIC_MEMBERS:
        raise SegmentError(f"A static segment holds at most {MAX_STATIC_MEMBERS} users")
    await session.execute(delete(SegmentMember).where(SegmentMember.segment_id == segment_id))
    wanted = sorted(set(user_ids))
    if not wanted:
        return
    known = set(await session.scalars(select(User.id).where(User.id.in_(wanted))))
    rows = [
        {"segment_id": segment_id, "user_id": user_id} for user_id in wanted if user_id in known
    ]
    if rows:
        await session.execute(insert(SegmentMember), rows)
