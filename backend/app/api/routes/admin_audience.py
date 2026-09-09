"""Audience side of the panel: segments and manual broadcasts.

Mounted under `/api/admin`. Nothing here sends anything synchronously except the test
message to the admin's own chat: a real broadcast is queued and delivered by the
`broadcast_queue` job, so a request never waits on thousands of Telegram calls.
"""

import uuid
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from telegram.error import TelegramError

from app.api.deps import AdminActor, SessionDep, require
from app.api.schemas import (
    AdminUserOut,
    BroadcastDeliveryOut,
    BroadcastIn,
    BroadcastMessageIn,
    BroadcastOut,
    BroadcastScheduleIn,
    BroadcastTestIn,
    SegmentFilterSpecOut,
    SegmentIn,
    SegmentOut,
    SegmentPreviewIn,
    SegmentPreviewOut,
)
from app.bot import broadcasting, runtime
from app.db.models import User
from app.services import billing, broadcasts, segments

router = APIRouter(prefix="/admin", tags=["admin"])

SegmentsViewer = Annotated[AdminActor, Depends(require("segments.view"))]
# Previews and the delivery log name concrete users, so they also need `users.view`.
SegmentsSampler = Annotated[AdminActor, Depends(require("segments.view", "users.view"))]
BroadcastsSampler = Annotated[AdminActor, Depends(require("broadcasts.view", "users.view"))]
SegmentsEditor = Annotated[AdminActor, Depends(require("segments.edit"))]
BroadcastsViewer = Annotated[AdminActor, Depends(require("broadcasts.view"))]
BroadcastsEditor = Annotated[AdminActor, Depends(require("broadcasts.edit"))]
BroadcastsSender = Annotated[AdminActor, Depends(require("broadcasts.send"))]


def _user_brief(user: User) -> AdminUserOut:
    """The few user fields the audience preview shows; no aggregates are computed."""
    return AdminUserOut(
        id=user.id,
        name=user.name,
        username=user.username or "",
        language=user.language,
        country=user.country,
        activity=user.activity,
        mainGoal=user.main_goal,
        plan=billing.effective_plan(user),
        birthDate=user.birth_date,
        createdAt=user.created_at,
        lastActiveAt=None,
        questionsTotal=0,
        conversations=0,
        paymentsStars=0,
        proExpiresAt=user.pro_expires_at,
        trialExpiresAt=user.trial_expires_at,
        proAutoRenew=bool(user.pro_auto_renew),
    )


def _segment_out(row: segments.SegmentRow, member_ids: list[int] | None = None) -> SegmentOut:
    segment = row.segment
    return SegmentOut(
        id=segment.id,
        name=segment.name,
        description=segment.description or "",
        kind=segment.kind,
        filters=dict(segment.filters or {}),
        size=row.size,
        memberCount=row.member_count,
        userIds=member_ids or [],
        createdBy=segment.created_by,
        createdAt=segment.created_at,
        updatedAt=segment.updated_at,
    )


# --- segments ----------------------------------------------------------------------------


@router.get("/segments/filters", response_model=list[SegmentFilterSpecOut])
async def segment_filters(_: SegmentsViewer) -> list[SegmentFilterSpecOut]:
    """The filter catalog the segment editor renders itself from."""
    return [
        SegmentFilterSpecOut(
            key=spec.key,
            kind=spec.kind,
            description=spec.description,
            options=list(spec.options),
        )
        for spec in segments.FILTER_SPECS
    ]


@router.get("/segments", response_model=list[SegmentOut])
async def list_segments(_: SegmentsViewer, session: SessionDep) -> list[SegmentOut]:
    return [_segment_out(row) for row in await segments.list_segments(session)]


@router.get("/segments/{segment_id}", response_model=SegmentOut)
async def get_segment(segment_id: uuid.UUID, _: SegmentsViewer, session: SessionDep) -> SegmentOut:
    row = await segments.get_segment(session, segment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    members = (
        await segments.segment_member_ids(session, segment_id)
        if row.segment.kind == "static"
        else []
    )
    return _segment_out(row, members)


@router.post("/segments", response_model=SegmentOut)
async def create_segment(
    payload: SegmentIn, actor: SegmentsEditor, session: SessionDep
) -> SegmentOut:
    try:
        row = await segments.create_segment(
            session,
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            filters=payload.filters,
            user_ids=payload.userIds,
            actor_id=actor.id,
        )
    except segments.SegmentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _segment_out(row)


@router.put("/segments/{segment_id}", response_model=SegmentOut)
async def update_segment(
    segment_id: uuid.UUID, payload: SegmentIn, actor: SegmentsEditor, session: SessionDep
) -> SegmentOut:
    try:
        row = await segments.update_segment(
            session,
            segment_id,
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            filters=payload.filters,
            user_ids=payload.userIds,
            actor_id=actor.id,
        )
    except segments.SegmentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if row is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return _segment_out(row)


@router.delete("/segments/{segment_id}", status_code=204)
async def delete_segment(segment_id: uuid.UUID, actor: SegmentsEditor, session: SessionDep) -> None:
    if not await segments.delete_segment(session, segment_id, actor_id=actor.id):
        raise HTTPException(status_code=404, detail="Segment not found")


@router.post("/segments/preview", response_model=SegmentPreviewOut)
async def preview_segment(
    payload: SegmentPreviewIn, _: SegmentsSampler, session: SessionDep
) -> SegmentPreviewOut:
    """Size, language split and a few example users for an unsaved definition."""
    if payload.kind == "static":
        if not payload.userIds:
            return SegmentPreviewOut(size=0, byLanguage={}, sample=[])
        # A pinned list is the `userIds` filter: one code path, and ids without a user row
        # are dropped exactly as they are when the segment is saved.
        audience = segments.Audience(
            kind="dynamic", filters={"userIds": sorted(set(payload.userIds))}
        )
    else:
        audience = segments.Audience(kind="dynamic", filters=payload.filters)
    try:
        size = await segments.count_audience(session, audience)
        by_language = await segments.audience_by_language(session, audience)
        sample = await segments.audience_sample(session, audience)
    except segments.SegmentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return SegmentPreviewOut(
        size=size, byLanguage=by_language, sample=[_user_brief(user) for user in sample]
    )


# --- broadcasts --------------------------------------------------------------------------


def _broadcast_out(row: broadcasts.BroadcastRow) -> BroadcastOut:
    broadcast = row.broadcast
    return BroadcastOut(
        id=broadcast.id,
        title=broadcast.title,
        category=broadcast.category,
        status=broadcast.status,
        segmentId=broadcast.segment_id,
        segmentName=row.segment_name,
        filters=dict(broadcast.filters or {}),
        content={
            language: BroadcastMessageIn(**message)
            for language, message in (broadcast.content or {}).items()
        },
        markdown=bool(broadcast.markdown),
        scheduledAt=broadcast.scheduled_at,
        startedAt=broadcast.started_at,
        finishedAt=broadcast.finished_at,
        totalRecipients=broadcast.total_recipients,
        sentCount=broadcast.sent_count,
        failedCount=broadcast.failed_count,
        blockedCount=broadcast.blocked_count,
        pendingCount=row.pending,
        createdBy=broadcast.created_by,
        createdAt=broadcast.created_at,
        updatedAt=broadcast.updated_at,
    )


def _content_dict(payload: BroadcastIn) -> dict:
    return {language: message.model_dump() for language, message in (payload.content or {}).items()}


@router.get("/broadcasts", response_model=list[BroadcastOut])
async def list_broadcasts(_: BroadcastsViewer, session: SessionDep) -> list[BroadcastOut]:
    return [_broadcast_out(row) for row in await broadcasts.list_broadcasts(session)]


@router.get("/broadcasts/{broadcast_id}", response_model=BroadcastOut)
async def get_broadcast(
    broadcast_id: uuid.UUID, _: BroadcastsViewer, session: SessionDep
) -> BroadcastOut:
    row = await broadcasts.get_broadcast(session, broadcast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return _broadcast_out(row)


@router.get("/broadcasts/{broadcast_id}/audience", response_model=SegmentPreviewOut)
async def broadcast_audience(
    broadcast_id: uuid.UUID, _: BroadcastsSampler, session: SessionDep
) -> SegmentPreviewOut:
    """Who the broadcast would reach if it started now (opt-outs already excluded)."""
    row = await broadcasts.get_broadcast(session, broadcast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    try:
        audience = await broadcasts.audience_for(session, row.broadcast)
        size = await segments.count_audience(session, audience)
        by_language = await segments.audience_by_language(session, audience)
        sample = await segments.audience_sample(session, audience)
    except (broadcasts.BroadcastError, segments.SegmentError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return SegmentPreviewOut(
        size=size, byLanguage=by_language, sample=[_user_brief(user) for user in sample]
    )


@router.post("/broadcasts", response_model=BroadcastOut)
async def create_broadcast(
    payload: BroadcastIn, actor: BroadcastsEditor, session: SessionDep
) -> BroadcastOut:
    try:
        row = await broadcasts.create_broadcast(
            session,
            title=payload.title,
            category=payload.category,
            segment_id=payload.segmentId,
            filters=payload.filters,
            content=_content_dict(payload),
            markdown=payload.markdown,
            actor_id=actor.id,
        )
    except (broadcasts.BroadcastError, segments.SegmentError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _broadcast_out(row)


@router.put("/broadcasts/{broadcast_id}", response_model=BroadcastOut)
async def update_broadcast(
    broadcast_id: uuid.UUID, payload: BroadcastIn, _: BroadcastsEditor, session: SessionDep
) -> BroadcastOut:
    try:
        row = await broadcasts.update_broadcast(
            session,
            broadcast_id,
            title=payload.title,
            category=payload.category,
            segment_id=payload.segmentId,
            filters=payload.filters,
            content=_content_dict(payload),
            markdown=payload.markdown,
        )
    except (broadcasts.BroadcastError, segments.SegmentError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return _broadcast_out(row)


@router.delete("/broadcasts/{broadcast_id}", status_code=204)
async def delete_broadcast(
    broadcast_id: uuid.UUID, _: BroadcastsEditor, session: SessionDep
) -> None:
    try:
        deleted = await broadcasts.delete_broadcast(session, broadcast_id)
    except broadcasts.BroadcastError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Broadcast not found")


@router.post("/broadcasts/{broadcast_id}/schedule", response_model=BroadcastOut)
async def schedule_broadcast(
    broadcast_id: uuid.UUID,
    payload: BroadcastScheduleIn,
    actor: BroadcastsSender,
    session: SessionDep,
) -> BroadcastOut:
    """Queue the broadcast. No timestamp means the next queue tick picks it up."""
    scheduled_at = payload.scheduledAt
    if scheduled_at is not None and scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    try:
        row = await broadcasts.schedule(
            session, broadcast_id, scheduled_at=scheduled_at, actor_id=actor.id
        )
    except (broadcasts.BroadcastError, segments.SegmentError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return _broadcast_out(row)


@router.post("/broadcasts/{broadcast_id}/cancel", response_model=BroadcastOut)
async def cancel_broadcast(
    broadcast_id: uuid.UUID, _: BroadcastsSender, session: SessionDep
) -> BroadcastOut:
    try:
        row = await broadcasts.cancel(session, broadcast_id)
    except broadcasts.BroadcastError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return _broadcast_out(row)


@router.post("/broadcasts/{broadcast_id}/test", status_code=204)
async def test_broadcast(
    broadcast_id: uuid.UUID,
    payload: BroadcastTestIn,
    actor: BroadcastsEditor,
    session: SessionDep,
) -> None:
    """Send the message to the admin's own chat, exactly as a recipient would see it."""
    row = await broadcasts.get_broadcast(session, broadcast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Bot is not running")
    # A copy of the admin's own row with the chosen language, so the preview matches what a
    # recipient in that language gets without touching the stored profile.
    recipient = User(id=actor.id, language=payload.language, name=actor.user.name)
    # Detach the broadcast (its columns stay loaded) and release the connection before the
    # Telegram call: a session is never held across a network send.
    broadcast = row.broadcast
    session.expunge(broadcast)
    await session.rollback()
    try:
        await broadcasting.deliver(application.bot, recipient, broadcast)
    except broadcasts.BroadcastError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TelegramError as error:
        raise HTTPException(status_code=502, detail=f"Telegram refused: {error}") from error


@router.get("/broadcasts/{broadcast_id}/deliveries", response_model=list[BroadcastDeliveryOut])
async def broadcast_deliveries(
    broadcast_id: uuid.UUID,
    _: BroadcastsSampler,
    session: SessionDep,
    status: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[BroadcastDeliveryOut]:
    rows, _total = await broadcasts.list_deliveries(
        session, broadcast_id, status=status, limit=limit, offset=offset
    )
    return [
        BroadcastDeliveryOut(
            userId=delivery.user_id,
            name=user.name if user else "",
            username=(user.username or "") if user else "",
            language=user.language if user else "",
            status=delivery.status,
            error=delivery.error or "",
            sentAt=delivery.sent_at,
        )
        for delivery, user in rows
    ]
