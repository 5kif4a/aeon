import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import DiaryEntryCreate, DiaryEntryOut
from app.services import diary

router = APIRouter(tags=["diary"])


@router.get("/diary", response_model=list[DiaryEntryOut])
async def list_diary(user: CurrentUser, session: SessionDep) -> list[DiaryEntryOut]:
    entries = await diary.list_entries(session, user.id)
    return [DiaryEntryOut.model_validate(entry) for entry in entries]


@router.post("/diary", response_model=DiaryEntryOut)
async def add_diary_entry(
    payload: DiaryEntryCreate, user: CurrentUser, session: SessionDep
) -> DiaryEntryOut:
    entry = await diary.add_entry(session, user.id, payload.text.strip())
    return DiaryEntryOut.model_validate(entry)


@router.delete("/diary/{entry_id}", status_code=204)
async def delete_diary_entry(entry_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    deleted = await diary.delete_entry(session, user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
