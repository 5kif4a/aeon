"""Product metrics for the ops group: /stats snapshots and daily/weekly/monthly digests."""

import html
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BillingPayment, Conversation, DailyUsage, User
from app.services import billing, events

PRO_EXPIRING_DAYS = 3


@dataclass
class Window:
    """Half-open UTC interval [since, until) with a human label."""

    label: str
    since: datetime
    until: datetime


@dataclass
class Stats:
    window: Window
    users_total: int = 0
    new_users: int = 0
    onboarding_completed: int = 0
    active_users: int = 0
    prompt_questions: int = 0
    rag_questions: int = 0
    council_questions: int = 0
    conversations_started: int = 0
    conversations_by_agent: dict[str, int] = field(default_factory=dict)
    trials_started: int = 0
    payments_count: int = 0
    payments_stars: int = 0
    subscriptions_canceled: int = 0
    limit_hits: int = 0
    generation_failures: int = 0
    pro_active: int = 0
    trial_active: int = 0
    pro_expiring_soon: int = 0
    pro_not_renewing: int = 0

    @property
    def questions_total(self) -> int:
        return self.prompt_questions + self.rag_questions + self.council_questions


def _zone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_now(now: datetime, tz_name: str) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(_zone(tz_name))


def _local_midnight(day: date, tz_name: str) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=_zone(tz_name)).astimezone(UTC)


def today_window(now: datetime, tz_name: str) -> Window:
    local = local_now(now, tz_name)
    return Window("today", _local_midnight(local.date(), tz_name), now.astimezone(UTC))


def last_days_window(now: datetime, tz_name: str, days: int) -> Window:
    """The last `days` days including today so far (used by `/stats 7`, `/stats 30`)."""
    local = local_now(now, tz_name)
    since = _local_midnight(local.date() - timedelta(days=days - 1), tz_name)
    return Window(f"last {days} days", since, now.astimezone(UTC))


def yesterday_window(today: date, tz_name: str) -> Window:
    day = today - timedelta(days=1)
    return Window(day.isoformat(), _local_midnight(day, tz_name), _local_midnight(today, tz_name))


def previous_week_window(today: date, tz_name: str) -> Window:
    since_day = today - timedelta(days=7)
    label = f"{since_day.isoformat()} – {(today - timedelta(days=1)).isoformat()}"
    return Window(label, _local_midnight(since_day, tz_name), _local_midnight(today, tz_name))


def previous_month_window(today: date, tz_name: str) -> Window:
    first_of_this_month = today.replace(day=1)
    last_month_day = first_of_this_month - timedelta(days=1)
    first_of_last_month = last_month_day.replace(day=1)
    return Window(
        first_of_last_month.strftime("%B %Y"),
        _local_midnight(first_of_last_month, tz_name),
        _local_midnight(first_of_this_month, tz_name),
    )


def digests_due(local: datetime, digest_hour: int) -> list[str]:
    """Which digests fire at this local time: daily every day, weekly on Monday, monthly on the 1st."""
    if local.hour != digest_hour:
        return []
    due = ["daily"]
    if local.weekday() == 0:
        due.append("weekly")
    if local.day == 1:
        due.append("monthly")
    return due


def digest_window(period: str, today: date, tz_name: str) -> Window:
    if period == "daily":
        return yesterday_window(today, tz_name)
    if period == "weekly":
        return previous_week_window(today, tz_name)
    if period == "monthly":
        return previous_month_window(today, tz_name)
    raise ValueError(f"Unknown digest period: {period}")


async def collect_stats(
    session: AsyncSession, window: Window, now: datetime | None = None
) -> Stats:
    current = (now or billing.utc_now()).astimezone(UTC)
    since, until = window.since, window.until
    stats = Stats(window=window)

    stats.users_total = await session.scalar(select(func.count()).select_from(User)) or 0
    stats.new_users = (
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= since, User.created_at < until)
        )
        or 0
    )

    # daily_usages is keyed by UTC date; a window's UTC dates approximate its bounds.
    usage_row = (
        await session.execute(
            select(
                func.count(func.distinct(DailyUsage.user_id)),
                func.coalesce(func.sum(DailyUsage.prompt_questions), 0),
                func.coalesce(func.sum(DailyUsage.rag_questions), 0),
                func.coalesce(func.sum(DailyUsage.council_questions), 0),
            ).where(
                DailyUsage.usage_date >= since.date(),
                DailyUsage.usage_date <= (until - timedelta(microseconds=1)).date(),
                (
                    DailyUsage.prompt_questions
                    + DailyUsage.rag_questions
                    + DailyUsage.council_questions
                )
                > 0,
            )
        )
    ).one()
    stats.active_users = usage_row[0] or 0
    stats.prompt_questions = int(usage_row[1])
    stats.rag_questions = int(usage_row[2])
    stats.council_questions = int(usage_row[3])

    agents = await session.execute(
        select(Conversation.agent_id, func.count())
        .where(Conversation.created_at >= since, Conversation.created_at < until)
        .group_by(Conversation.agent_id)
        .order_by(func.count().desc())
    )
    stats.conversations_by_agent = {agent_id: count for agent_id, count in agents.all()}
    stats.conversations_started = sum(stats.conversations_by_agent.values())

    payment_row = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(BillingPayment.amount), 0)).where(
                BillingPayment.status == "paid",
                BillingPayment.created_at >= since,
                BillingPayment.created_at < until,
            )
        )
    ).one()
    stats.payments_count = payment_row[0] or 0
    stats.payments_stars = int(payment_row[1])

    counts = await events.count_by_type(session, since, until)
    stats.onboarding_completed = counts.get(events.ONBOARDING_COMPLETED, 0)
    stats.trials_started = counts.get(events.TRIAL_STARTED, 0)
    stats.subscriptions_canceled = counts.get(events.SUBSCRIPTION_CANCELED, 0)
    stats.limit_hits = counts.get(events.QUESTION_LIMIT_HIT, 0)
    stats.generation_failures = counts.get(events.GENERATION_FAILED, 0)

    pro_active = User.pro_expires_at > current
    trial_active = and_(User.trial_expires_at > current, ~func.coalesce(pro_active, False))
    plan_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(case((pro_active, 1), else_=0)), 0),
                func.coalesce(func.sum(case((trial_active, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    pro_active,
                                    User.pro_expires_at
                                    <= current + timedelta(days=PRO_EXPIRING_DAYS),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(case((and_(pro_active, User.pro_auto_renew.is_(False)), 1), else_=0)),
                    0,
                ),
            )
        )
    ).one()
    stats.pro_active = int(plan_row[0])
    stats.trial_active = int(plan_row[1])
    stats.pro_expiring_soon = int(plan_row[2])
    stats.pro_not_renewing = int(plan_row[3])
    return stats


def format_stats(stats: Stats, title: str) -> str:
    """Telegram HTML for the ops group (internal, English only)."""
    lines = [f"<b>{html.escape(title)}</b> · {html.escape(stats.window.label)}", ""]
    lines += [
        "<b>Users</b>",
        f"• new: {stats.new_users} · onboarded: {stats.onboarding_completed}",
        f"• active: {stats.active_users} · total: {stats.users_total}",
        "",
        "<b>Questions</b>",
        f"• total: {stats.questions_total} (prompt {stats.prompt_questions}, "
        f"rag {stats.rag_questions}, council {stats.council_questions})",
        f"• limit hits: {stats.limit_hits} · generation failures: {stats.generation_failures}",
    ]
    if stats.conversations_by_agent:
        agents = ", ".join(
            f"{html.escape(agent)} {count}" for agent, count in stats.conversations_by_agent.items()
        )
        lines.append(f"• conversations: {stats.conversations_started} ({agents})")
    lines += [
        "",
        "<b>Revenue</b>",
        f"• payments: {stats.payments_count} · {stats.payments_stars} ★",
        f"• trials started: {stats.trials_started} · canceled: {stats.subscriptions_canceled}",
        "",
        "<b>Now</b>",
        f"• Pro: {stats.pro_active} (expiring ≤{PRO_EXPIRING_DAYS}d: {stats.pro_expiring_soon}, "
        f"not renewing: {stats.pro_not_renewing}) · Trial: {stats.trial_active}",
    ]
    return "\n".join(lines)
