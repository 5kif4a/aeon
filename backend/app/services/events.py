"""Append-only product event log: the data layer behind ops notifications and digests.

Services record events inside the caller's transaction (same commit as the state change);
the bot/API layer decides what to announce via `app.services.ops`.
"""

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProductEvent

# Event type names. Keep them stable: digests and future dashboards group by them.
USER_CREATED = "user_created"
ONBOARDING_COMPLETED = "onboarding_completed"
TRIAL_STARTED = "trial_started"
PAYMENT_SUCCEEDED = "payment_succeeded"
SUBSCRIPTION_CANCELED = "subscription_canceled"
SUBSCRIPTION_RESTORED = "subscription_restored"
SUBSCRIPTION_PAYMENT_FAILED = "subscription_payment_failed"
PAYMENT_REFUNDED = "payment_refunded"
PAYSUPPORT_REQUEST = "paysupport_request"
QUESTION_LIMIT_HIT = "question_limit_hit"
GENERATION_FAILED = "generation_failed"
OPS_DIGEST_SENT = "ops_digest_sent"
PRO_GRANTED = "pro_granted"
ADMIN_LOGIN = "admin_login"
ADMIN_VIEW_CONVERSATION = "admin_view_conversation"
ADMIN_SETTING_CHANGED = "admin_setting_changed"
ADMIN_PROMPT_PREVIEW = "admin_prompt_preview"
ADMIN_ROLE_CHANGED = "admin_role_changed"
ADMIN_ACCESS_GRANTED = "admin_access_granted"
ADMIN_ACCESS_CHANGED = "admin_access_changed"
ADMIN_ACCESS_REVOKED = "admin_access_revoked"
SEGMENT_CHANGED = "segment_changed"
BROADCAST_QUEUED = "broadcast_queued"
BROADCAST_FINISHED = "broadcast_finished"
MARKETING_OPTED_OUT = "marketing_opted_out"


def record(
    session: AsyncSession, event_type: str, user_id: int | None = None, **payload
) -> ProductEvent:
    """Stage an event on the session; the caller's commit persists it."""
    event = ProductEvent(user_id=user_id, type=event_type, payload=_jsonable(payload))
    session.add(event)
    return event


async def count_by_type(session: AsyncSession, since: datetime, until: datetime) -> dict[str, int]:
    result = await session.execute(
        select(ProductEvent.type, func.count())
        .where(ProductEvent.created_at >= since, ProductEvent.created_at < until)
        .group_by(ProductEvent.type)
    )
    return {event_type: count for event_type, count in result.all()}


async def last_event_at(
    session: AsyncSession, event_type: str, **payload_filter
) -> datetime | None:
    query = select(func.max(ProductEvent.created_at)).where(ProductEvent.type == event_type)
    for key, value in payload_filter.items():
        query = query.where(ProductEvent.payload[key].astext == str(value))
    return await session.scalar(query)


def _jsonable(payload: dict) -> dict:
    result = {}
    for key, value in payload.items():
        if isinstance(value, datetime):
            value = value.astimezone(UTC).isoformat() if value.tzinfo else value.isoformat()
        elif isinstance(value, date):
            value = value.isoformat()
        result[key] = value
    return result
