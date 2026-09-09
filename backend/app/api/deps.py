from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import admin_auth
from app.core.telegram_auth import InitDataError, extract_telegram_user, validate_init_data
from app.db.models import User
from app.db.session import get_session
from app.services import admin_access, users

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str, Header()] = "",
) -> User:
    """Authenticate via `Authorization: tma <initData>` header."""
    scheme, _, init_data_raw = authorization.partition(" ")
    if scheme.lower() != "tma" or not init_data_raw:
        raise HTTPException(status_code=401, detail="Missing Telegram initData")

    try:
        init_data = validate_init_data(init_data_raw)
        telegram_user = extract_telegram_user(init_data)
    except InitDataError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    return await users.get_or_create_user(
        session,
        int(telegram_user["id"]),
        name=telegram_user.get("first_name", ""),
        username=telegram_user.get("username", "") or "",
        language=telegram_user.get("language_code", ""),
    )


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass
class AdminActor:
    """The authenticated admin plus the permissions their role grants."""

    user: User
    identity: admin_access.AdminIdentity

    @property
    def id(self) -> int:
        return self.user.id

    def can(self, permission: str) -> bool:
        return self.identity.can(permission)


async def get_admin_actor(
    session: SessionDep,
    authorization: Annotated[str, Header()] = "",
) -> AdminActor:
    """Admin panel auth: `tma <initData>` inside Telegram or `admin <token>` in a browser.

    Either way the Telegram user id must hold panel access: a row in `admin_accounts` (there
    is no env allowlist). What they may *do* is decided per route by `require(...)`; this
    dependency only proves they are an admin at all.
    """
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() == "admin":
        try:
            user_id = admin_auth.verify_session_token(credential)
        except admin_auth.AdminAuthError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        # Deliberately not `get_or_create_user`: a token holder logged in once, so their row
        # exists. Creating one here would fake a signup in the product metrics.
        found = await users.get_user(session, user_id)
        if found is None:
            raise HTTPException(status_code=403, detail="Admin access required")
        user = found
    else:
        user = await get_current_user(session, authorization)

    identity = await admin_access.resolve_identity(session, user.id)
    if identity is None:
        raise HTTPException(status_code=403, detail="Admin access required")
    return AdminActor(user=user, identity=identity)


AdminActorDep = Annotated[AdminActor, Depends(get_admin_actor)]


def require(*permissions: str) -> Callable[..., Coroutine[Any, Any, AdminActor]]:
    """Route dependency: the admin must hold every listed permission.

    403 with the missing key in the detail, so the panel can explain the refusal instead of
    showing an empty screen.
    """

    async def dependency(actor: AdminActorDep) -> AdminActor:
        for permission in permissions:
            if not actor.can(permission):
                raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
        return actor

    return dependency
