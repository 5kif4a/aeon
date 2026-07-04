from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
        language=telegram_user.get("language_code", ""),
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
