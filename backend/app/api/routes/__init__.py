from fastapi import APIRouter

from app.api.routes import agents, diary, goal, me

api_router = APIRouter(prefix="/api")
api_router.include_router(me.router)
api_router.include_router(goal.router)
api_router.include_router(diary.router)
api_router.include_router(agents.router)
