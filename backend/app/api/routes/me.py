from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import (
    NotificationSettingsOut,
    NotificationSettingsUpdate,
    ProfileOut,
    ProfileUpdate,
)
from app.services import admin_access, users

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser, session: SessionDep) -> ProfileOut:
    # `isAdmin` only decides whether the Mini App shows the panel link; the panel itself
    # re-checks every request against the role matrix.
    is_admin = await admin_access.resolve_identity(session, user.id) is not None
    return ProfileOut.from_user(user, is_admin=is_admin)


@router.patch("/me", response_model=ProfileOut)
async def update_me(payload: ProfileUpdate, user: CurrentUser, session: SessionDep) -> ProfileOut:
    fields = payload.to_user_fields()
    if fields:
        user = await users.update_user(session, user, fields)
    is_admin = await admin_access.resolve_identity(session, user.id) is not None
    return ProfileOut.from_user(user, is_admin=is_admin)


@router.get("/me/notifications", response_model=NotificationSettingsOut)
async def get_notification_settings(user: CurrentUser) -> NotificationSettingsOut:
    return NotificationSettingsOut.from_user(user)


@router.patch("/me/notifications", response_model=NotificationSettingsOut)
async def update_notification_settings(
    payload: NotificationSettingsUpdate, user: CurrentUser, session: SessionDep
) -> NotificationSettingsOut:
    """Delivery hour and time zone are the same columns the bot's /settings writes."""
    fields = payload.to_user_fields()
    if fields:
        user = await users.update_user(session, user, fields)
    return NotificationSettingsOut.from_user(user)
