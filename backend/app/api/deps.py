from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import admin_auth
from app.core.telegram_auth import InitDataError, extract_telegram_user, validate_init_data
from app.db.models import User
from app.db.session import get_session
from app.services import users

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


async def get_admin_user(
    session: SessionDep,
    authorization: Annotated[str, Header()] = "",
) -> User:
    """Admin panel auth: `tma <initData>` inside Telegram or `admin <token>` in a browser.

    Either way the Telegram user id must be in `OPS_ADMIN_IDS`.
    """
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() == "admin":
        try:
            user_id = admin_auth.verify_session_token(credential)
        except admin_auth.AdminAuthError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        if not admin_auth.is_admin(user_id):
            raise HTTPException(status_code=403, detail="Admin access required")
        user = await users.get_or_create_user(session, user_id)
        return user

    user = await get_current_user(session, authorization)
    if not admin_auth.is_admin(user.id):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]
