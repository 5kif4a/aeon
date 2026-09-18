from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import (
    NotificationSettingsOut,
    NotificationSettingsUpdate,
    ProfileOut,
    ProfileUpdate,
)
from app.services import admin_access, events, ops, users

router = APIRouter(tags=["profile"])


# How often an open of the Mini App is written down; every screen calls /me.
WEBAPP_OPEN_STAMP_INTERVAL = timedelta(hours=1)


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser, session: SessionDep) -> ProfileOut:
    # Opening the Mini App is a reaction: it restarts the notification decay and tells the
    # bot it no longer has to point at the app under every answer.
    now = datetime.now(UTC)
    if (
        user.last_webapp_open_at is None
        or user.last_webapp_open_at < now - WEBAPP_OPEN_STAMP_INTERVAL
    ):
        user = await users.update_user(
            session, user, {"last_webapp_open_at": now, "unanswered_notifications": 0}
        )
    # `isAdmin` only decides whether the Mini App shows the panel link; the panel itself
    # re-checks every request against the role matrix.
    is_admin = await admin_access.resolve_identity(session, user.id) is not None
    return ProfileOut.from_user(user, is_admin=is_admin)


@router.patch("/me", response_model=ProfileOut)
async def update_me(payload: ProfileUpdate, user: CurrentUser, session: SessionDep) -> ProfileOut:
    fields = payload.to_user_fields()
    # The first birth date completes onboarding: count it, and skip that day's reminders so the
    # user is not pinged minutes after filling in the form.
    first_birth_date = user.birth_date is None and fields.get("birth_date") is not None
    if first_birth_date:
        today = users.local_datetime(user).date()
        fields.setdefault("last_daily_notification_date", today)
        fields.setdefault("last_life_weekly_date", today)
        events.record(
            session, events.ONBOARDING_COMPLETED, user.id, birth_date=fields["birth_date"]
        )
    if fields:
        user = await users.update_user(session, user, fields)
    if first_birth_date:
        ops.onboarding_completed(user)
    is_admin = await admin_access.resolve_identity(session, user.id) is not None
    return ProfileOut.from_user(user, is_admin=is_admin)


@router.get("/me/notifications", response_model=NotificationSettingsOut)
async def get_notification_settings(user: CurrentUser) -> NotificationSettingsOut:
    return NotificationSettingsOut.from_user(user)


@router.patch("/me/notifications", response_model=NotificationSettingsOut)
async def update_notification_settings(
    payload: NotificationSettingsUpdate, user: CurrentUser, session: SessionDep
) -> NotificationSettingsOut:
    """Delivery hours and time zone are the same columns the bot's /settings writes."""
    fields = payload.to_user_fields(user)
    if fields:
        user = await users.update_user(session, user, fields)
    return NotificationSettingsOut.from_user(user)
