"""Read models and privileged actions for the product-owner panel (`/api/admin/*`)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Date, DateTime, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BillingPayment,
    Conversation,
    ConversationMessage,
    DailyUsage,
    ProductEvent,
    User,
)
from app.services import billing, events

MAX_PAGE = 200


def _ordering(expression, order: str):
    """One ORDER BY term. NULLs always sort last so empty cells never lead a page."""
    clause = expression.asc() if order == "asc" else expression.desc()
    return clause.nulls_last()


def _order_by(columns: dict, sort: str, order: str, default: str, tiebreaker):
    """Resolve a client sort key against the columns a list actually offers.

    An unknown key falls back to the list's default instead of failing: sort keys travel in
    the URL, and a stale link should still open the screen. The tiebreaker keeps paging
    stable when the sorted column repeats itself.
    """
    expression = columns.get(sort, columns[default])
    return [_ordering(expression, order), tiebreaker.desc()]


def _plan_rank(now: datetime):
    """Plans sort by value (Pro > Trial > Free), not by the alphabet."""
    return case((User.pro_expires_at > now, 2), (User.trial_expires_at > now, 1), else_=0)


def _plan_expression(now: datetime):
    return case(
        (User.pro_expires_at > now, "Pro"),
        (User.trial_expires_at > now, "Trial"),
        else_="Free",
    )


@dataclass
class UserRow:
    user: User
    plan: str
    questions_total: int
    last_active_at: datetime | None
    conversations: int
    payments_stars: int


@dataclass
class Page:
    items: list
    total: int


async def list_users(
    session: AsyncSession,
    *,
    query: str = "",
    plan: str = "",
    sort: str = "created",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> Page:
    current = now or billing.utc_now()
    plan_expr = _plan_expression(current)
    usage = (
        select(
            DailyUsage.user_id.label("user_id"),
            func.coalesce(
                func.sum(
                    DailyUsage.prompt_questions
                    + DailyUsage.rag_questions
                    + DailyUsage.council_questions
                ),
                0,
            ).label("questions"),
            func.max(DailyUsage.usage_date).label("last_usage"),
        )
        .group_by(DailyUsage.user_id)
        .subquery()
    )
    convs = (
        select(
            Conversation.user_id.label("user_id"),
            func.count().label("conversations"),
            func.max(Conversation.updated_at).label("last_conversation"),
        )
        .group_by(Conversation.user_id)
        .subquery()
    )
    payments = (
        select(
            BillingPayment.user_id.label("user_id"),
            func.coalesce(func.sum(BillingPayment.amount), 0).label("stars"),
        )
        .where(BillingPayment.status == "paid")
        .group_by(BillingPayment.user_id)
        .subquery()
    )

    base = (
        select(
            User,
            plan_expr.label("plan"),
            func.coalesce(usage.c.questions, 0),
            convs.c.last_conversation,
            usage.c.last_usage,
            func.coalesce(convs.c.conversations, 0),
            func.coalesce(payments.c.stars, 0),
        )
        .outerjoin(usage, usage.c.user_id == User.id)
        .outerjoin(convs, convs.c.user_id == User.id)
        .outerjoin(payments, payments.c.user_id == User.id)
    )
    filters = []
    text = query.strip()
    if text:
        if text.lstrip("-").isdigit():
            filters.append(User.id == int(text))
        else:
            pattern = f"%{text}%"
            filters.append(
                or_(
                    User.name.ilike(pattern),
                    User.country.ilike(pattern),
                    User.activity.ilike(pattern),
                )
            )
    if plan in ("Free", "Trial", "Pro"):
        filters.append(plan_expr == plan)
    if filters:
        base = base.where(*filters)

    # `last_active` repeats in SQL what the loop below computes in Python: the later of the
    # last conversation and the last usage day. `greatest` ignores NULLs in Postgres, so a
    # user with only one of the two still sorts by it.
    sort_columns = {
        "created": User.created_at,
        "name": User.name,
        "plan": _plan_rank(current),
        "country": User.country,
        "questions": func.coalesce(usage.c.questions, 0),
        "conversations": func.coalesce(convs.c.conversations, 0),
        "stars": func.coalesce(payments.c.stars, 0),
        "lastActive": func.greatest(
            convs.c.last_conversation, cast(usage.c.last_usage, DateTime(timezone=True))
        ),
    }

    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.execute(
        base.order_by(*_order_by(sort_columns, sort, order, "created", User.id))
        .limit(min(limit, MAX_PAGE))
        .offset(offset)
    )
    items = []
    for user, plan_value, questions, last_conversation, last_usage, conversations, stars in rows:
        last_active = last_conversation
        if last_usage is not None:
            usage_dt = datetime.combine(last_usage, datetime.min.time(), tzinfo=UTC)
            if last_active is None or usage_dt > last_active:
                last_active = usage_dt
        items.append(
            UserRow(
                user=user,
                plan=plan_value,
                questions_total=int(questions),
                last_active_at=last_active,
                conversations=int(conversations),
                payments_stars=int(stars),
            )
        )
    return Page(items=items, total=int(total))


@dataclass
class UserDetail:
    user: User
    plan: str
    usage_30d: dict[str, int]
    payments: list[BillingPayment]
    conversations: list[Conversation]
    events: list[ProductEvent]


async def get_user_detail(
    session: AsyncSession, user_id: int, now: datetime | None = None
) -> UserDetail | None:
    user = await session.get(User, user_id)
    if user is None:
        return None
    current = now or billing.utc_now()
    since = (current - timedelta(days=30)).date()
    usage_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(DailyUsage.prompt_questions), 0),
                func.coalesce(func.sum(DailyUsage.rag_questions), 0),
                func.coalesce(func.sum(DailyUsage.council_questions), 0),
            ).where(DailyUsage.user_id == user_id, DailyUsage.usage_date >= since)
        )
    ).one()
    payments = list(
        await session.scalars(
            select(BillingPayment)
            .where(BillingPayment.user_id == user_id)
            .order_by(BillingPayment.created_at.desc())
            .limit(50)
        )
    )
    conversations = list(
        await session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(30)
        )
    )
    recent_events = list(
        await session.scalars(
            select(ProductEvent)
            .where(ProductEvent.user_id == user_id)
            .order_by(ProductEvent.created_at.desc())
            .limit(50)
        )
    )
    return UserDetail(
        user=user,
        plan=billing.effective_plan(user, current),
        usage_30d={
            "prompt": int(usage_row[0]),
            "rag": int(usage_row[1]),
            "council": int(usage_row[2]),
        },
        payments=payments,
        conversations=conversations,
        events=recent_events,
    )


@dataclass
class ConversationRow:
    conversation: Conversation
    user_name: str
    user_username: str
    user_language: str
    user_plan: str
    preview: str


async def list_conversations(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    agent_id: str = "",
    status: str = "",
    sort: str = "updated",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> Page:
    current = now or billing.utc_now()
    first_message = (
        select(ConversationMessage.text)
        .where(
            ConversationMessage.conversation_id == Conversation.id,
            ConversationMessage.role == "user",
        )
        .order_by(ConversationMessage.position)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    base = select(
        Conversation,
        User.name,
        User.username,
        User.language,
        _plan_expression(current),
        first_message,
    ).join(User, User.id == Conversation.user_id)
    if user_id is not None:
        base = base.where(Conversation.user_id == user_id)
    if agent_id:
        base = base.where(Conversation.agent_id == agent_id)
    if status in ("active", "closed"):
        base = base.where(Conversation.status == status)

    sort_columns = {
        "updated": Conversation.updated_at,
        "created": Conversation.created_at,
        "agent": Conversation.agent_id,
        "status": Conversation.status,
        "messages": Conversation.message_count,
        "user": User.name,
    }

    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.execute(
        base.order_by(*_order_by(sort_columns, sort, order, "updated", Conversation.id))
        .limit(min(limit, MAX_PAGE))
        .offset(offset)
    )
    items = [
        ConversationRow(
            conversation=conversation,
            user_name=name or "",
            user_username=username or "",
            user_language=language,
            user_plan=plan,
            preview=(preview or "")[:160],
        )
        for conversation, name, username, language, plan, preview in rows
    ]
    return Page(items=items, total=int(total))


async def get_conversation(
    session: AsyncSession, conversation_id: uuid.UUID
) -> tuple[Conversation, User | None, list[ConversationMessage]] | None:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        return None
    user = await session.get(User, conversation.user_id)
    messages = list(
        await session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.position)
        )
    )
    return conversation, user, messages


PAYMENT_SORTS = {
    "date": BillingPayment.created_at,
    "user": BillingPayment.user_id,
    "amount": BillingPayment.amount,
    "status": BillingPayment.status,
    "until": BillingPayment.subscription_expires_at,
}


async def list_payments(
    session: AsyncSession,
    *,
    sort: str = "date",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Page:
    total = await session.scalar(select(func.count()).select_from(BillingPayment)) or 0
    rows = await session.execute(
        select(BillingPayment, User.language, User.country)
        .join(User, User.id == BillingPayment.user_id)
        .order_by(*_order_by(PAYMENT_SORTS, sort, order, "date", BillingPayment.id))
        .limit(min(limit, MAX_PAGE))
        .offset(offset)
    )
    return Page(items=list(rows.all()), total=int(total))


async def grant_pro(
    session: AsyncSession,
    user_id: int,
    *,
    days: int,
    granted_by: int,
    now: datetime | None = None,
) -> User | None:
    """Support action: extend (or start) Pro without a payment. Recorded as an event."""
    current = now or billing.utc_now()
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        return None
    start = (
        user.pro_expires_at if user.pro_expires_at and user.pro_expires_at > current else current
    )
    user.pro_expires_at = start + timedelta(days=days)
    user.plan = "Pro"
    events.record(
        session,
        events.PRO_GRANTED,
        user_id,
        days=days,
        granted_by=granted_by,
        expires_at=user.pro_expires_at,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def record_admin_event(
    session: AsyncSession, event_type: str, admin_id: int, **payload
) -> None:
    events.record(session, event_type, admin_id, **payload)
    await session.commit()


@dataclass
class DailyPoint:
    day: date
    new_users: int = 0
    active_users: int = 0
    questions: int = 0
    payments_stars: int = 0
    payments_count: int = 0


async def daily_series(session: AsyncSession, since: datetime, until: datetime) -> list[DailyPoint]:
    """Per-UTC-day series for the dashboard charts."""
    points: dict[date, DailyPoint] = {}
    day = since.astimezone(UTC).date()
    last_day = (until.astimezone(UTC) - timedelta(microseconds=1)).date()
    while day <= last_day:
        points[day] = DailyPoint(day=day)
        day += timedelta(days=1)

    created_day = cast(User.created_at, Date)
    for created, count in await session.execute(
        select(created_day, func.count())
        .where(User.created_at >= since, User.created_at < until)
        .group_by(created_day)
    ):
        if created in points:
            points[created].new_users = int(count)

    for usage_day, active, questions in await session.execute(
        select(
            DailyUsage.usage_date,
            func.count(func.distinct(DailyUsage.user_id)),
            func.coalesce(
                func.sum(
                    DailyUsage.prompt_questions
                    + DailyUsage.rag_questions
                    + DailyUsage.council_questions
                ),
                0,
            ),
        )
        .where(DailyUsage.usage_date >= since.date(), DailyUsage.usage_date <= last_day)
        .group_by(DailyUsage.usage_date)
    ):
        if usage_day in points:
            points[usage_day].active_users = int(active)
            points[usage_day].questions = int(questions)

    paid_day = cast(BillingPayment.created_at, Date)
    for paid, count, stars in await session.execute(
        select(paid_day, func.count(), func.coalesce(func.sum(BillingPayment.amount), 0))
        .where(
            BillingPayment.status == "paid",
            BillingPayment.created_at >= since,
            BillingPayment.created_at < until,
        )
        .group_by(paid_day)
    ):
        if paid in points:
            points[paid].payments_count = int(count)
            points[paid].payments_stars = int(stars)
    return list(points.values())
