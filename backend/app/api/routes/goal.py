from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import GoalCreate, GoalOut
from app.services import goals

router = APIRouter(tags=["goal"])


@router.get("/goal", response_model=GoalOut | None)
async def get_goal(user: CurrentUser, session: SessionDep) -> GoalOut | None:
    goal = await goals.get_active_goal(session, user.id)
    return GoalOut.model_validate(goal) if goal else None


@router.post("/goal", response_model=GoalOut)
async def set_goal(payload: GoalCreate, user: CurrentUser, session: SessionDep) -> GoalOut:
    goal = await goals.set_goal(session, user.id, payload.text.strip())
    return GoalOut.model_validate(goal)


@router.post("/goal/close", response_model=GoalOut)
async def close_goal(user: CurrentUser, session: SessionDep) -> GoalOut:
    goal = await goals.close_active_goal(session, user.id)
    if goal is None:
        raise HTTPException(status_code=404, detail="No active goal")
    return GoalOut.model_validate(goal)
