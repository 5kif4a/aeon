from fastapi import APIRouter

from app.api.routes import admin, agents, billing, conversations, diary, goal, me

api_router = APIRouter(prefix="/api")
api_router.include_router(me.router)
api_router.include_router(goal.router)
api_router.include_router(diary.router)
api_router.include_router(agents.router)
api_router.include_router(conversations.router)
api_router.include_router(billing.router)
api_router.include_router(admin.router)
