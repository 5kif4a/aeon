from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import ProfileOut, ProfileUpdate
from app.services import users

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser) -> ProfileOut:
    return ProfileOut.from_user(user)


@router.patch("/me", response_model=ProfileOut)
async def update_me(payload: ProfileUpdate, user: CurrentUser, session: SessionDep) -> ProfileOut:
    fields = payload.to_user_fields()
    if fields:
        user = await users.update_user(session, user, fields)
    return ProfileOut.from_user(user)
