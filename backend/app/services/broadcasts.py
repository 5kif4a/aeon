"""Manual broadcasts: compose, queue, send, report.

A broadcast is composed in the admin panel and sent by the `broadcast_queue` job, never
inside a request: the audience can be thousands of chats and Telegram is rate limited.
Queueing writes one `broadcast_deliveries` row per recipient, so the send is resumable and
idempotent - a restart continues with the rows still `pending` instead of sending twice.

`category` decides who is in the audience: `marketing` respects `users.marketing_enabled`,
`service` (outages, policy or pricing changes) reaches everyone the filter matches.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Broadcast, BroadcastDelivery, User, UserSegment
from app.i18n import DEFAULT_LANGUAGE
from app.services import events, segments

DRAFT = "draft"
SCHEDULED = "scheduled"
SENDING = "sending"
SENT = "sent"
CANCELED = "canceled"
FAILED = "failed"

MARKETING = "marketing"
SERVICE = "service"

# Statuses the queue job picks up.
RUNNABLE = (SCHEDULED, SENDING)
# Statuses that still allow editing the content and the audience. A scheduled campaign is
# not among them: cancel it first (which needs `broadcasts.send`), otherwise an editor could
# change what someone else already queued and the job would send the new version.
EDITABLE = (DRAFT, CANCELED, FAILED)
# One Telegram message; `messaging.split_message` would otherwise chunk and a partial send
# could be retried or misrecorded per chunk.
MAX_TEXT_LENGTH = 3500
# Rows per INSERT when freezing an audience (see `materialize`).
INSERT_CHUNK = 1000


class BroadcastError(ValueError):
    """Rejected broadcast operation (empty content, wrong status, unknown segment)."""


@dataclass
class Message:
    text: str
    button_text: str = ""
    button_url: str = ""


@dataclass
class BroadcastRow:
    broadcast: Broadcast
    segment_name: str
    pending: int


def _message_from(raw: dict) -> Message:
    return Message(
        text=str(raw.get("text") or "").strip(),
        button_text=str(raw.get("buttonText") or "").strip(),
        button_url=str(raw.get("buttonUrl") or "").strip(),
    )


def render(broadcast: Broadcast, language: str) -> Message:
    """Pick the message for a language: exact match, then the default, then anything set."""
    content = broadcast.content or {}
    for candidate in (language, DEFAULT_LANGUAGE):
        raw = content.get(candidate)
        if raw and str(raw.get("text") or "").strip():
            return _message_from(raw)
    for raw in content.values():
        if raw and str(raw.get("text") or "").strip():
            return _message_from(raw)
    raise BroadcastError("The broadcast has no text")


def validate_content(content: dict) -> dict:
    """Every filled language needs text; a button needs both a label and a URL."""
    clean: dict = {}
    for language, raw in (content or {}).items():
        message = _message_from(raw if isinstance(raw, dict) else {})
        if not message.text and not message.button_text and not message.button_url:
            continue
        if not message.text:
            raise BroadcastError(f"{language}: the message text is required")
        if len(message.text) > MAX_TEXT_LENGTH:
            raise BroadcastError(f"{language}: the message is over {MAX_TEXT_LENGTH} characters")
        if bool(message.button_text) != bool(message.button_url):
            raise BroadcastError(f"{language}: a button needs both a label and a URL")
        if message.button_url and not message.button_url.startswith(("https://", "tg://")):
            raise BroadcastError(f"{language}: the button URL must be https:// or tg://")
        clean[language] = {
            "text": message.text,
            "buttonText": message.button_text,
            "buttonUrl": message.button_url,
        }
    if not clean:
        raise BroadcastError("Write the message in at least one language")
    return clean


async def audience_for(session: AsyncSession, broadcast: Broadcast) -> segments.Audience:
    """The audience this broadcast will reach right now.

    An empty definition is refused rather than read as "everyone": a deleted segment nulls
    `segment_id`, and a campaign must never widen itself to the whole user base by accident.
    """
    respect_opt_out = broadcast.category == MARKETING
    if broadcast.segment_id is not None:
        segment = await session.get(UserSegment, broadcast.segment_id)
        if segment is None:
            raise BroadcastError("The segment this broadcast points at is gone")
        if segment.kind == "dynamic" and not segment.filters:
            raise BroadcastError("The segment has no conditions; add at least one")
        return segments.audience_for(segment, respect_opt_out=respect_opt_out)
    filters = dict(broadcast.filters or {})
    if not filters:
        raise BroadcastError("Pick a segment or at least one filter")
    return segments.Audience(kind="dynamic", filters=filters, respect_opt_out=respect_opt_out)


# --- reads -------------------------------------------------------------------------------


async def _describe(session: AsyncSession, broadcast: Broadcast) -> BroadcastRow:
    segment_name = ""
    if broadcast.segment_id is not None:
        segment_name = (
            await session.scalar(
                select(UserSegment.name).where(UserSegment.id == broadcast.segment_id)
            )
            or ""
        )
    pending = int(
        await session.scalar(
            select(func.count())
            .select_from(BroadcastDelivery)
            .where(
                BroadcastDelivery.broadcast_id == broadcast.id,
                BroadcastDelivery.status == "pending",
            )
        )
        or 0
    )
    return BroadcastRow(broadcast=broadcast, segment_name=segment_name, pending=pending)


async def list_broadcasts(session: AsyncSession, *, limit: int = 100) -> list[BroadcastRow]:
    rows = list(
        await session.scalars(select(Broadcast).order_by(Broadcast.created_at.desc()).limit(limit))
    )
    return [await _describe(session, broadcast) for broadcast in rows]


async def get_broadcast(session: AsyncSession, broadcast_id: uuid.UUID) -> BroadcastRow | None:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        return None
    return await _describe(session, broadcast)


async def list_deliveries(
    session: AsyncSession,
    broadcast_id: uuid.UUID,
    *,
    status: str = "",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[tuple[BroadcastDelivery, User | None]], int]:
    base = (
        select(BroadcastDelivery, User)
        .outerjoin(User, User.id == BroadcastDelivery.user_id)
        .where(BroadcastDelivery.broadcast_id == broadcast_id)
    )
    if status:
        base = base.where(BroadcastDelivery.status == status)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.execute(
        base.order_by(BroadcastDelivery.created_at, BroadcastDelivery.user_id)
        .limit(limit)
        .offset(offset)
    )
    return list(rows.all()), int(total)


# --- writes ------------------------------------------------------------------------------


async def create_broadcast(
    session: AsyncSession,
    *,
    title: str,
    category: str,
    segment_id: uuid.UUID | None,
    filters: dict,
    content: dict,
    markdown: bool,
    actor_id: int,
) -> BroadcastRow:
    broadcast = Broadcast(
        title=title.strip(),
        category=category,
        status=DRAFT,
        segment_id=segment_id,
        filters=segments.validate_filters(filters) if segment_id is None else {},
        content=validate_content(content),
        markdown=markdown,
        created_by=actor_id,
    )
    session.add(broadcast)
    await session.commit()
    # `updated_at` is expired by the commit (server-side onupdate); reload before reading it.
    await session.refresh(broadcast)
    return await _describe(session, broadcast)


async def update_broadcast(
    session: AsyncSession,
    broadcast_id: uuid.UUID,
    *,
    title: str,
    category: str,
    segment_id: uuid.UUID | None,
    filters: dict,
    content: dict,
    markdown: bool,
) -> BroadcastRow | None:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        return None
    if broadcast.status not in EDITABLE:
        raise BroadcastError(f"A {broadcast.status} broadcast cannot be edited")
    broadcast.title = title.strip()
    broadcast.category = category
    broadcast.segment_id = segment_id
    broadcast.filters = segments.validate_filters(filters) if segment_id is None else {}
    broadcast.content = validate_content(content)
    broadcast.markdown = markdown
    await session.commit()
    await session.refresh(broadcast)
    return await _describe(session, broadcast)


async def delete_broadcast(session: AsyncSession, broadcast_id: uuid.UUID) -> bool:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        return False
    if broadcast.status == SENDING:
        raise BroadcastError("Cancel the broadcast before deleting it")
    await session.delete(broadcast)
    await session.commit()
    return True


async def schedule(
    session: AsyncSession,
    broadcast_id: uuid.UUID,
    *,
    scheduled_at: datetime | None,
    actor_id: int,
    now: datetime | None = None,
) -> BroadcastRow | None:
    """Queue a broadcast: `scheduled_at=None` means as soon as the job runs next."""
    current = now or datetime.now(UTC)
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        return None
    if broadcast.status in (SENDING, SENT):
        raise BroadcastError(f"This broadcast is already {broadcast.status}")
    validate_content(broadcast.content or {})
    # Fails here rather than in the job when the audience no longer resolves - including a
    # saved filter the current build no longer accepts, which only surfaces when the
    # conditions are actually built.
    audience = await audience_for(session, broadcast)
    audience.select_users(current)
    broadcast.status = SCHEDULED
    broadcast.scheduled_at = scheduled_at
    broadcast.finished_at = None
    events.record(
        session,
        events.BROADCAST_QUEUED,
        actor_id,
        broadcast_id=str(broadcast.id),
        category=broadcast.category,
        scheduled_at=scheduled_at or current,
    )
    await session.commit()
    await session.refresh(broadcast)
    return await _describe(session, broadcast)


async def cancel(session: AsyncSession, broadcast_id: uuid.UUID) -> BroadcastRow | None:
    """Stop a queued or running broadcast; messages already sent stay sent."""
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        return None
    if broadcast.status not in RUNNABLE:
        raise BroadcastError(f"A {broadcast.status} broadcast cannot be canceled")
    # Pending rows are kept, not deleted: the job may be sending to a batch of them right
    # now and has to be able to record the result, and a re-scheduled campaign must skip
    # everyone who already got it. The rows simply stay pending and show as "not reached".
    broadcast.status = CANCELED
    broadcast.finished_at = datetime.now(UTC)
    await session.commit()
    await refresh_counters(session, broadcast)
    await session.refresh(broadcast)
    return await _describe(session, broadcast)


# --- queue -------------------------------------------------------------------------------


async def due_broadcasts(session: AsyncSession, now: datetime | None = None) -> list[Broadcast]:
    """Broadcasts the job should work on: due schedules first, then unfinished sends."""
    current = now or datetime.now(UTC)
    return list(
        await session.scalars(
            select(Broadcast)
            .where(
                Broadcast.status.in_(RUNNABLE),
                (Broadcast.scheduled_at.is_(None)) | (Broadcast.scheduled_at <= current),
            )
            .order_by(Broadcast.status.desc(), Broadcast.scheduled_at.nulls_first())
        )
    )


async def materialize(
    session: AsyncSession, broadcast: Broadcast, now: datetime | None = None
) -> int | None:
    """Freeze the audience into `broadcast_deliveries` and mark the broadcast as sending.

    Safe to call again on a broadcast already being sent: existing rows are kept, so a
    recipient is never queued twice, and users who joined the segment meanwhile are added.
    Returns None when the broadcast was canceled between the job reading it and this
    commit - the status change is compare-and-set, so the admin's cancel is never overwritten.
    """
    current = now or datetime.now(UTC)
    audience = await audience_for(session, broadcast)
    user_ids = list(
        await session.scalars(
            audience.select_users(current).with_only_columns(User.id).order_by(User.id)
        )
    )
    # executemany in slices: a single multi-row VALUES would hit asyncpg's 32767-argument
    # limit at ~6.5k recipients.
    for offset in range(0, len(user_ids), INSERT_CHUNK):
        rows = [
            {"broadcast_id": broadcast.id, "user_id": user_id, "status": "pending"}
            for user_id in user_ids[offset : offset + INSERT_CHUNK]
        ]
        await session.execute(
            insert(BroadcastDelivery).on_conflict_do_nothing(
                constraint="uq_broadcast_deliveries_recipient"
            ),
            rows,
        )
    if broadcast.category == MARKETING:
        # Someone who opted out after the campaign was queued must not get it on resume.
        opted_out = select(User.id).where(User.marketing_enabled.is_(False))
        await session.execute(
            delete(BroadcastDelivery).where(
                BroadcastDelivery.broadcast_id == broadcast.id,
                BroadcastDelivery.status == "pending",
                BroadcastDelivery.user_id.in_(opted_out),
            )
        )
    total = int(
        await session.scalar(
            select(func.count())
            .select_from(BroadcastDelivery)
            .where(BroadcastDelivery.broadcast_id == broadcast.id)
        )
        or 0
    )
    result = await session.execute(
        update(Broadcast)
        .where(Broadcast.id == broadcast.id, Broadcast.status.in_(RUNNABLE))
        .values(
            status=SENDING,
            total_recipients=total,
            started_at=func.coalesce(Broadcast.started_at, current),
        )
    )
    await session.commit()
    if result.rowcount == 0:
        return None
    await session.refresh(broadcast)
    return total


async def next_pending(
    session: AsyncSession, broadcast_id: uuid.UUID, limit: int
) -> list[tuple[uuid.UUID, User]]:
    """The next recipients to write to, with the user rows the message is rendered for."""
    rows = await session.execute(
        select(BroadcastDelivery.id, User)
        .join(User, User.id == BroadcastDelivery.user_id)
        .where(
            BroadcastDelivery.broadcast_id == broadcast_id,
            BroadcastDelivery.status == "pending",
        )
        .order_by(BroadcastDelivery.user_id)
        .limit(limit)
    )
    return [(delivery_id, user) for delivery_id, user in rows.all()]


async def mark_deliveries(
    session: AsyncSession,
    results: list[tuple[uuid.UUID, str, str]],
    now: datetime | None = None,
) -> None:
    """Write `(delivery_id, status, error)` send results.

    Plain Core updates, one per row: a row may legitimately be gone (the user opted out and
    `materialize` dropped it while the batch was in flight), and the ORM bulk update would
    raise on the missing match and lose the whole batch.
    """
    current = now or datetime.now(UTC)
    for delivery_id, status, error in results:
        await session.execute(
            update(BroadcastDelivery)
            .where(BroadcastDelivery.id == delivery_id)
            .values(
                status=status,
                error=error[:500],
                sent_at=current if status == "sent" else None,
            )
        )
    await session.commit()


async def refresh_counters(session: AsyncSession, broadcast: Broadcast) -> int:
    """Recount the per-status totals from the delivery log; returns how many are pending."""
    counts = dict(
        (
            await session.execute(
                select(BroadcastDelivery.status, func.count())
                .where(BroadcastDelivery.broadcast_id == broadcast.id)
                .group_by(BroadcastDelivery.status)
            )
        ).all()
    )
    broadcast.sent_count = int(counts.get("sent", 0))
    broadcast.failed_count = int(counts.get("failed", 0))
    broadcast.blocked_count = int(counts.get("blocked", 0))
    await session.commit()
    return int(counts.get("pending", 0))


async def finish(session: AsyncSession, broadcast: Broadcast, now: datetime | None = None) -> None:
    broadcast.status = SENT
    broadcast.finished_at = now or datetime.now(UTC)
    events.record(
        session,
        events.BROADCAST_FINISHED,
        broadcast.created_by,
        broadcast_id=str(broadcast.id),
        category=broadcast.category,
        sent=broadcast.sent_count,
        failed=broadcast.failed_count,
        blocked=broadcast.blocked_count,
    )
    await session.commit()
